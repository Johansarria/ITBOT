from database.database_manager import create_tables

def main():
    """
    Initializes the discarded_signals table by calling the central table creation utility.
    """
    create_tables()
    print("Tabla discarded_signals inicializada.")

if __name__ == "__main__":
    main()
