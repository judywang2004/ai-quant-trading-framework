//+------------------------------------------------------------------+
//| ExportHistory.mq5                                                |
//| AI Quant Trading Framework                                       |
//+------------------------------------------------------------------+
//
// STATUS: UNCOMPILED / UNVERIFIED (2026-10-16).
// The filename fix below was written without access to MetaEditor or an
// MT5 terminal. Compile and run it once before trusting its output.
// Known, still-open issues (not fixed here):
//   - FILE_CSV without an explicit delimiter may write tab-separated
//     values; neither data/mt4_csv_loader.py (Date,Time,O,H,L,C,V) nor
//     data/csv_loader.py (timestamp,open,...) has been checked against
//     this script's actual output.
//   - Timestamps are broker server time with no UTC offset.
//   - MqlRates.spread and real_volume are not exported.
//
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

   // Name the file after the timeframe actually exported. This was
   // previously hard-coded to "_M5", so exporting M15 produced a file
   // named USDJPY_M5.csv containing M15 bars.
   // EnumToString(PERIOD_M15) == "PERIOD_M15" -> "M15"
   string timeframeName = EnumToString(Timeframe);
   StringReplace(timeframeName, "PERIOD_", "");

   string filename =
      SymbolName + "_" + timeframeName + ".csv";

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