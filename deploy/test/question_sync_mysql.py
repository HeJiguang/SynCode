"""Exercise the real migration in an isolated, disposable native MySQL 8 instance.

Usage: python deploy/test/question_sync_mysql.py --mysql-bin E:/develop/mysql-8.0.34-winx64/bin
No project credentials or existing databases are used.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import socket
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mysql-bin', type=Path, required=True)
    args = parser.parse_args()
    suffix = '.exe' if __import__('os').name == 'nt' else ''
    server = args.mysql_bin / ('mysqld' + suffix)
    client = args.mysql_bin / ('mysql' + suffix)
    flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if suffix else {}
    with tempfile.TemporaryDirectory(prefix='syncode-question-mysql-') as temporary:
        data = Path(temporary) / 'data'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        init = subprocess.run([str(server), '--no-defaults', '--initialize-insecure',
                               f'--datadir={data}'], capture_output=True, **flags)
        if init.returncode:
            raise RuntimeError(init.stderr.decode(errors='replace'))
        with (Path(temporary) / 'server.log').open('wb') as log:
            process = subprocess.Popen([str(server), '--no-defaults', f'--datadir={data}',
                '--bind-address=127.0.0.1', f'--port={port}', '--mysqlx=0',
                '--skip-log-bin'], stdout=log, stderr=log, **flags)

            def sql(statement, database=True):
                command = [str(client), '--no-defaults', '--host=127.0.0.1', f'--port={port}',
                           '--user=root', '--batch', '--skip-column-names', '--default-character-set=utf8mb4']
                if database:
                    command.append('question_sync_test')
                result = subprocess.run(command, input=statement, encoding='utf-8',
                                        capture_output=True, **flags)
                if result.returncode:
                    raise RuntimeError(result.stderr)
                return result.stdout.strip()

            try:
                for attempt in range(60):
                    try:
                        sql('SELECT 1;', False)
                        break
                    except RuntimeError:
                        if process.poll() is not None:
                            raise RuntimeError((Path(temporary) / 'server.log').read_text(errors='replace'))
                        time.sleep(0.5)
                else:
                    raise RuntimeError('Temporary MySQL did not start')
                sql('CREATE DATABASE question_sync_test CHARACTER SET utf8mb4;', False)
                sql('CREATE TABLE tb_question(question_id BIGINT UNSIGNED PRIMARY KEY, content LONGTEXT) ENGINE=InnoDB;'
                    "INSERT INTO tb_question VALUES(1,'baseline');")
                migration = Path(__file__).parents[1] / 'migrations/mysql/versioned/V2026102801__question_outbox.sql'
                sql(migration.read_text(encoding='utf-8'))
                assert sql('SELECT COUNT(*) FROM tb_question_outbox;') == '2'
                sql("START TRANSACTION; INSERT INTO tb_question VALUES(2,'rollback'); ROLLBACK;")
                assert sql('SELECT COUNT(*) FROM tb_question_sync_state WHERE question_id=2;') == '0'
                assert sql('SELECT COUNT(*) FROM tb_question_outbox;') == '2'
                sql("INSERT INTO tb_question VALUES(2,'importer');")
                assert sql('SELECT revision FROM tb_question_sync_state WHERE question_id=2;') == '1'
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda i: sql(f"UPDATE tb_question SET content='edit{i}' WHERE question_id=2;"), range(12)))
                assert sql('SELECT revision FROM tb_question_sync_state WHERE question_id=2;') == '13'
                assert sql('SELECT COUNT(*) FROM tb_question_outbox WHERE question_id=2;') == '26'
                sql('START TRANSACTION; DELETE FROM tb_question WHERE question_id=2; ROLLBACK;')
                assert sql('SELECT revision FROM tb_question_sync_state WHERE question_id=2;') == '13'
                sql('DELETE FROM tb_question WHERE question_id=2;')
                assert sql('SELECT CONCAT(revision,\':\',deleted) FROM tb_question_sync_state WHERE question_id=2;') == '14:1'
                sql("INSERT INTO tb_question VALUES(2,'restored');")
                assert sql('SELECT CONCAT(revision,\':\',deleted) FROM tb_question_sync_state WHERE question_id=2;') == '15:0'
                # Polling/lease SQL is valid on MySQL 8 and claims only one row.
                sql("UPDATE tb_question_outbox SET status='SENDING',lease_token='test',available_at=TIMESTAMPADD(SECOND,60,UTC_TIMESTAMP(3)) "
                    "WHERE status IN ('PENDING','SENDING','SENT') AND available_at<=UTC_TIMESTAMP(3) ORDER BY available_at,id LIMIT 1;")
                assert sql("SELECT COUNT(*) FROM tb_question_outbox WHERE lease_token='test';") == '1'
                print('PASS: migration, baseline, importer insert, rollback, 12 concurrent updates, delete tombstone, reinsert, lease claim')
            finally:
                try:
                    sql('SHUTDOWN;', False)
                except RuntimeError:
                    process.terminate()
                process.wait(timeout=30)


if __name__ == '__main__':
    main()
