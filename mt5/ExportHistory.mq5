//+------------------------------------------------------------------+
//| ExportHistory.mq5                                                |
//| AI Quant Trading Framework                                       |
//+------------------------------------------------------------------+
#property script_show_inputs

input string SymbolName = "USDJPY";
input ENUM_TIMEFRAMES Timeframe = PERIOD_M5;
input int BarsToExport = 50000;

void OnStart()
{
   MqlRates rates[];

   int copied = CopyRates(
      SymbolName,
      Timeframe,
      0,
      BarsToExport,
      rates);

   if(copied <= 0)
   {
      Print("Failed to load history.");
      return;
   }

   ArraySetAsSeries(rates,false);

   string filename =
      SymbolName + "_M5.csv";

   int file = FileOpen(
      filename,
      FILE_WRITE | FILE_CSV);

   if(file == INVALID_HANDLE)
   {
      Print("Cannot create file.");
      return;
   }

   FileWrite(
      file,
      "timestamp",
      "open",
      "high",
      "low",
      "close",
      "volume");

   for(int i=0;i<ArraySize(rates);i++)
   {
      FileWrite(
         file,
         TimeToString(
            rates[i].time,
            TIME_DATE|TIME_MINUTES),
         rates[i].open,
         rates[i].high,
         rates[i].low,
         rates[i].close,
         rates[i].tick_volume);
   }

   FileClose(file);

   Print("Export complete.");
   Print(filename);
}