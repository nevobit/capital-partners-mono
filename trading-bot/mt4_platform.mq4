//+------------------------------------------------------------------+
//|                                           OrderBlockBot.mq4     |
//|                      Copyright 2024, Néstor                      |
//|                                         https://www.metaquotes.net/ |
//+------------------------------------------------------------------+
input string ConfigFile = "bot_config.txt"; // Archivo de configuración
double lotSize;
double stopLoss;
double takeProfit;
string symbol;
bool active;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    ReadConfig(); // Leer la configuración al inicio
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
}

//+------------------------------------------------------------------+
//| Leer la configuración desde el archivo                           |
//+------------------------------------------------------------------+
void ReadConfig()
{
    string config = "";
    int fileHandle = FileOpen(ConfigFile, FILE_READ);
    if (fileHandle != INVALID_HANDLE)
    {
        config = FileReadString(fileHandle);
        FileClose(fileHandle);
        ParseConfig(config); // Parsear la configuración
    }
    else
    {
        Print("Error al abrir el archivo de configuración.");
    }
}

//+------------------------------------------------------------------+
//| Parsear la configuración                                         |
//+------------------------------------------------------------------+
void ParseConfig(string config)
{
    // Ejemplo de configuración: "EURUSD,0.1,50,100,true"
    string tokens[];
    StringSplit(config, ',', tokens);
    
    if (ArraySize(tokens) >= 5)
    {
        symbol = tokens[0];
        lotSize = StringToDouble(tokens[1]);
        stopLoss = StringToDouble(tokens[2]);
        takeProfit = StringToDouble(tokens[3]);
        active = StringToBool(tokens[4]); // Leer estado activo/inactivo
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    ReadConfig(); // Leer la configuración en cada tick

    if (active) // Si el bot está activo
    {
        if (DetectOrderBlock()) // Detectar un Order Block
        {
            if (ConditionsToBuy()) // Definir la condición para comprar
            {
                PlaceBuyOrder();
            }
            else if (ConditionsToSell()) // Definir la condición para vender
            {
                PlaceSellOrder();
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Detectar Order Blocks                                           |
//+------------------------------------------------------------------+
bool DetectOrderBlock()
{
    double currentPrice = Close[0];
    double previousHigh = iHigh(symbol, 0, 1); // Alto anterior
    double previousLow = iLow(symbol, 0, 1); // Bajo anterior

    // Ejemplo simplificado de detección de Order Block
    if (currentPrice > previousHigh)
    {
        // Posible Order Block alcista
        return true;
    }
    else if (currentPrice < previousLow)
    {
        // Posible Order Block bajista
        return true;
    }
    return false;
}

//+------------------------------------------------------------------+
//| Colocar orden de compra                                          |
//+------------------------------------------------------------------+
void PlaceBuyOrder()
{
    double price = Ask;
    double sl = price - stopLoss * Point;
    double tp = price + takeProfit * Point;

    // Abrir orden de compra
    int ticket = OrderSend(symbol, OP_BUY, lotSize, price, 3, sl, tp, "Buy Order", 0, 0, clrGreen);
    if (ticket < 0)
    {
        Print("Error al abrir la orden de compra: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| Colocar orden de venta                                           |
//+------------------------------------------------------------------+
void PlaceSellOrder()
{
    double price = Bid;
    double sl = price + stopLoss * Point;
    double tp = price - takeProfit * Point;

    // Abrir orden de venta
    int ticket = OrderSend(symbol, OP_SELL, lotSize, price, 3, sl, tp, "Sell Order", 0, 0, clrRed);
    if (ticket < 0)
    {
        Print("Error al abrir la orden de venta: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| Define las condiciones para comprar                              |
//+------------------------------------------------------------------+
bool ConditionsToBuy()
{
    // Implementar la lógica de compra aquí
    return true; // Cambiar según tus condiciones
}

//+------------------------------------------------------------------+
//| Define las condiciones para vender                               |
//+------------------------------------------------------------------+
bool ConditionsToSell()
{
    // Implementar la lógica de venta aquí
    return true; // Cambiar según tus condiciones
}
//+------------------------------------------------------------------+
