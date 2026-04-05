from app.services.remote_db_config_service import RemoteDatabaseConfigService


def test_remote_db_config_service_saves_and_loads_active_config(session) -> None:
    service = RemoteDatabaseConfigService(session)

    saved = service.save_active_config(
        host="101.96.200.76",
        port=3306,
        database_name="onlineoj",
        username="root",
        password="secret",
    )

    loaded = service.get_active_config()

    assert loaded is not None
    assert loaded.config_id == saved.config_id
    assert loaded.host == "101.96.200.76"
    assert loaded.database_name == "onlineoj"
    assert service.build_database_url(loaded).startswith("mysql+pymysql://root:secret@101.96.200.76:3306/onlineoj")
