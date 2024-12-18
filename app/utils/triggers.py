from app.db.database import database


async def create_trigger_log_skin_sale():
    check_function = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'log_skin_sale'
    );
    """
    function_exists = await database.fetch_val(check_function)

    if not function_exists:
        create_function = """
        CREATE OR REPLACE FUNCTION log_skin_sale()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO history (user_id, action_type, description)
            VALUES (NEW.seller_id, 'sell', 'skin_id: ' || NEW.skin_id || ', price: ' || NEW.price);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        await database.execute(create_function)

    check_trigger = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trigger_log_skin_sale'
    );
    """
    trigger_exists = await database.fetch_val(check_trigger)

    if not trigger_exists:
        create_trigger = """
        CREATE TRIGGER trigger_log_skin_sale
        AFTER INSERT ON skin_sales
        FOR EACH ROW
        EXECUTE FUNCTION log_skin_sale();
        """
        await database.execute(create_trigger)


async def create_trigger_log_remove_skin_sale():
    check_function = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'log_remove_skin_sale'
    );
    """
    function_exists = await database.fetch_val(check_function)

    if not function_exists:
        create_function = """
        CREATE OR REPLACE FUNCTION log_remove_skin_sale()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO history (user_id, action_type, description)
            VALUES ((SELECT user_id FROM inventory WHERE skin_id = OLD.skin_id),
                    'remove_sell', 'skin_id: ' || OLD.skin_id);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
        """
        await database.execute(create_function)

    check_trigger = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trigger_log_remove_skin_sale'
    );
    """
    trigger_exists = await database.fetch_val(check_trigger)

    if not trigger_exists:
        create_trigger = """
        CREATE TRIGGER trigger_log_remove_skin_sale
        AFTER DELETE ON skin_sales
        FOR EACH ROW
        EXECUTE FUNCTION log_remove_skin_sale();
        """
        await database.execute(create_trigger)


async def create_trigger_log_balance_update():
    check_function = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'log_balance_update'
    );
    """
    function_exists = await database.fetch_val(check_function)

    if not function_exists:
        create_function = """
        CREATE OR REPLACE FUNCTION log_balance_update()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO history (user_id, action_type, description)
            VALUES (NEW.id, 'update_balance', 'new_balance: ' || NEW.balance);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        await database.execute(create_function)

    check_trigger = """
    SELECT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trigger_log_balance_update'
    );
    """
    trigger_exists = await database.fetch_val(check_trigger)

    if not trigger_exists:
        create_trigger = """
        CREATE TRIGGER trigger_log_balance_update
        AFTER UPDATE OF balance ON users
        FOR EACH ROW
        EXECUTE FUNCTION log_balance_update();
        """
        await database.execute(create_trigger)


async def initialize_triggers():
    await create_trigger_log_skin_sale()
    await create_trigger_log_remove_skin_sale()
    await create_trigger_log_balance_update()
