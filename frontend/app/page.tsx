"use client";

import { useState } from "react";
import StrategyForm from "../components/StrategyForm";
import ResultsPanel from "../components/ResultsPanel";

type StrategyFormData = {
  base_order_size: number;
  min_momentum: number;
  max_token_ask: number;
  take_profit: number;
  stop_loss: number;
  min_time_remaining: number;
  max_time_remaining: number;
};

type PricePoint = {
  time: string;
  price: number;
};

type ResultData = {
  metrics?: {
    pnl: number;
    sharpe: number;
    max_drawdown: number;
    trade_count: number;
  };
  price_series?: PricePoint[];
  error?: string;
  details?: string;
  stderr?: string;
  stdout?: string;
  raw_output?: string;
};

export default function HomePage() {
  const [formData, setFormData] = useState<StrategyFormData>({
    base_order_size: 20,
    min_momentum: 0.0005,
    max_token_ask: 0.65,
    take_profit: 0.05,
    stop_loss: 0.03,
    min_time_remaining: 30,
    max_time_remaining: 240,
  });

  const [result, setResult] = useState<ResultData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runBacktest = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      console.log("Sending request...");

      const res = await fetch("http://localhost:8000/backtest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      console.log("Status:", res.status);

      const text = await res.text();
      console.log("RAW:", text);

      try {
        const data = JSON.parse(text);
        setResult(data);

        if (!res.ok) {
          setError(data?.error || "Backend error");
        }
      } catch {
        setError("Invalid JSON from backend:\n" + text);
      }
    } catch (err) {
      console.error("FETCH ERROR:", err);
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="mx-auto max-w-6xl">
        <h1 className="mb-2 text-4xl font-bold">Strategy Playground</h1>
        <p className="mb-4 text-lg text-gray-700">
          Welcome! This website is designed for beginners who want to explore
          trading strategies without needing prior quantitative finance
          experience.
        </p>

        <div className="mb-8 rounded-xl border bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-2xl font-semibold">What this website does</h2>
          <p className="mb-3 text-gray-700">
            This tool lets you adjust a few strategy settings and test how that
            strategy would have performed on past Bitcoin market data. This is
            called a <span className="font-medium">backtest</span>.
          </p>
          <p className="mb-3 text-gray-700">
            Instead of trading with real money, you can safely experiment here
            first. You can change settings, run the strategy, and review the
            results to better understand how different choices affect trading
            performance.
          </p>
          <p className="text-gray-700">
            Think of this as a beginner-friendly trading sandbox: you are not
            predicting the future, but learning how strategy decisions may work
            under real historical market conditions.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <StrategyForm
            formData={formData}
            setFormData={setFormData}
            onSubmit={runBacktest}
            loading={loading}
          />

          <ResultsPanel
            result={result}
            loading={loading}
            error={error}
          />
        </div>
      </div>
    </main>
  );
}