from sqlalchemy.orm import Session
from sqlalchemy import text


def get_all_agents(db: Session):
    query = text("""
        SELECT extension, firstname AS first_name, lastname AS last_name
        FROM directory_search
    """)
    result = db.execute(query).fetchall()
    return [
        {
            "extension": row[0],
            "first_name": row[1],
            "last_name": row[2]
        }
        for row in result
    ]