from sqlalchemy import create_engine, text

from app.services.oj_reader import OJReader


def test_oj_reader_loads_existing_questions_from_configured_database(settings, tmp_path) -> None:
    target_db = tmp_path / "oj.db"
    engine = create_engine(f"sqlite:///{target_db}", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tb_question (
                    question_id BIGINT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    algorithm_tag TEXT,
                    knowledge_tags TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO tb_question (question_id, title, content, algorithm_tag, knowledge_tags)
                VALUES (1, 'Two Sum', 'Given nums and target.', 'Hash Table', 'array,hash')
                """
            )
        )

    settings.oj_database_url = f"sqlite:///{target_db}"
    reader = OJReader(settings)

    questions = reader.load_existing_questions()

    assert len(questions) == 1
    assert questions[0].title == "Two Sum"
    assert questions[0].algorithm_tag == "Hash Table"
