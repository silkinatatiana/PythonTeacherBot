from typing import Optional, Dict, List, Tuple
import asyncpg


class DataBase:
    def __init__(self):
        self.pool = None

    async def create_pool(self, pool):
        self.pool = pool
        await self.create_table()

    async def create_table(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS python_tasks (
                    id SERIAL PRIMARY KEY,
                    task TEXT NOT NULL,
                    section TEXT NOT NULL,
                    subsection TEXT NOT NULL
                )
            """)

    async def show_table(self, section: Optional[str] = None, subsection: Optional[str] = None) -> List[Tuple]:
        async with self.pool.acquire() as conn:
            sql = 'SELECT task FROM python_tasks'
            params = []
            conditions = []

            if section:
                conditions.append('section = $1')
                params.append(section)
            if subsection:
                conditions.append('subsection = $2')
                params.append(subsection)

            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)

            return await conn.fetch(sql, *params)


class UserStates:
    def __init__(self, db: DataBase):
        self.db = db

    async def create_table(self):
        async with self.db.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    section TEXT,
                    subsection TEXT,
                    task TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

    async def get_latest_status(self, user_id):
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM user_states 
                WHERE user_id = $1 AND is_active = TRUE
                ORDER BY created_at DESC 
                LIMIT 1
            """, user_id)
            return dict(row) if row else None

    async def update_status(self, user_id: int, **kwargs) -> None:
        columns = ['user_id', 'status'] + list(kwargs.keys())
        values = [user_id, kwargs.get('status', 'active')] + list(kwargs.values())

        placeholders = ', '.join([f'${i + 1}' for i in range(len(values))])
        columns_str = ', '.join(columns)

        async with self.db.pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO user_states ({columns_str}) VALUES ({placeholders})",
                *values
            )

    async def delete_user(self, user_id: int) -> None:
        async with self.db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE user_states 
                SET is_active = FALSE 
                WHERE user_id = $1
            """, user_id)