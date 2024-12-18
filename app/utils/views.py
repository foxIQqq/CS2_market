from app.db.database import database

async def create_user_purchases_view():
    query = """
    CREATE OR REPLACE VIEW user_purchases_view AS
    SELECT
        u.id AS user_id,
        u.username AS buyer_username,
        s.id AS skin_id,
        s.name AS skin_name,
        s.rarity AS skin_rarity,
        s.type AS skin_type,
        t.price AS purchase_price,
        t.created_at AS purchase_date
    FROM 
        transactions t
    JOIN 
        users u ON t.buyer_id = u.id
    JOIN 
        skins s ON t.skin_id = s.id;
    """
    await database.execute(query)

async def initialize_views():
    await create_user_purchases_view()
