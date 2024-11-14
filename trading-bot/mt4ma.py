def main():
    client = MT4Client()
    
    # Obtener datos históricos
    df = client.get_rates("EURUSD", 15, 100)  # 100 velas M15
    print(df.head())
    
    # Colocar orden
    ticket = client.place_order(
        symbol="EURUSD",
        order_type=0,  # 0 = BUY, 1 = SELL
        volume=0.1,
        price=1.1000,
        sl=1.0950,
        tp=1.1050,
        magic=12345
    )
    print(f"Orden colocada: {ticket}")
    
    # Ver posiciones abiertas
    positions = client.get_positions()
    print(f"Posiciones abiertas: {positions}")

main()