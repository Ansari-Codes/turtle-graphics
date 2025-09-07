import asyncpg
import os
database_url = os.environ.get('DATABASE_URL')
async def get_db_conn():
    if not database_url:
        raise ValueError("Cannot find database url")
    return await asyncpg.connect(database_url)
