-- Destructive rollback: removes all non-Java starter programs stored in this column.
ALTER TABLE tb_question DROP COLUMN starter_code_json;
