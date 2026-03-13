def main():
    from src.agent import bandit
    from src.config import settings
    from src.data import simulator
    from src.db.mongo_client import db

    db[settings.collection_trends].drop()
    db[settings.collection_configs].drop()
    db[settings.collection_replay].drop()
    print("Collections cleared.")

    simulator.run_simulation()
    bandit.main()


if __name__ == "__main__":
    main()
