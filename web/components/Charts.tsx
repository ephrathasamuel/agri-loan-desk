"use client";

import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { InsuranceYear, Season } from "@/lib/types";

const C = {
  normal: "#3b82f6",
  dry: "#f59e0b",
  loss: "#dc2626",
  paid: "#16a34a",
  smallLoss: "#a3a3a3",
  none: "#cbd5e1",
  line: "#475569",
};

const axis = { fontSize: 11, fill: "#64748b" };

function Frame({ children, label }: { children: React.ReactElement; label: string }) {
  return (
    <div className="h-64 w-full" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
    </div>
  );
}

export function SeasonRainChart({ seasons, median, dryLimit }: {
  seasons: Season[]; median: number; dryLimit: number;
}) {
  return (
    <Frame label="Season rainfall by year">
      <BarChart data={seasons} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={axis} interval="preserveStartEnd" minTickGap={14} />
        <YAxis tick={axis} width={42} unit="" />
        <Tooltip
          formatter={(v) => [`${Number(v).toFixed(0)} mm`, "Season rain"]}
          labelFormatter={(y) => `Season ${y}`}
        />
        <ReferenceLine y={median} stroke={C.line} label={{ value: "median", position: "insideTopRight", fontSize: 11, fill: C.line }} />
        <ReferenceLine y={dryLimit} stroke={C.dry} strokeDasharray="5 4"
          label={{ value: "dry below", position: "insideBottomRight", fontSize: 11, fill: "#b45309" }} />
        <Bar dataKey="season_rain_mm" isAnimationActive={false}>
          {seasons.map((s) => <Cell key={s.year} fill={s.dry ? C.dry : C.normal} />)}
        </Bar>
      </BarChart>
    </Frame>
  );
}

export function YieldLossChart({ seasons, badThreshold }: { seasons: Season[]; badThreshold: number }) {
  const data = seasons.map((s) => ({ year: s.year, loss: +(s.yield_loss * 100).toFixed(1) }));
  return (
    <Frame label="Estimated yield loss from water stress by year">
      <BarChart data={data} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={axis} interval="preserveStartEnd" minTickGap={14} />
        <YAxis tick={axis} width={42} unit="%" domain={[0, (max: number) => Math.max(30, Math.ceil(max / 10) * 10)]} />
        <Tooltip formatter={(v) => [`${v}%`, "Yield loss"]} labelFormatter={(y) => `Season ${y}`} />
        <ReferenceLine y={badThreshold * 100} stroke={C.loss} strokeDasharray="5 4"
          label={{ value: "bad season", position: "insideTopRight", fontSize: 11, fill: C.loss }} />
        <Bar dataKey="loss" isAnimationActive={false}>
          {data.map((d) => <Cell key={d.year} fill={d.loss >= badThreshold * 100 ? C.loss : "#fca5a5"} />)}
        </Bar>
      </BarChart>
    </Frame>
  );
}

export function PayoutChart({ years, trigger, exit }: { years: InsuranceYear[]; trigger: number; exit: number }) {
  const colour = (y: InsuranceYear) =>
    y.flag === "paid" ? C.paid : y.flag === "loss not covered" ? C.loss : y.flag === "paid, small loss" ? C.smallLoss : C.none;
  return (
    <Frame label="Insurance index rainfall by year with trigger and exit">
      <BarChart data={years} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="year" tick={axis} interval="preserveStartEnd" minTickGap={14} />
        <YAxis tick={axis} width={42} />
        <Tooltip
          formatter={(v, _n, item) => {
            const y = item.payload as InsuranceYear;
            return [`${Number(v).toFixed(0)} mm, payout ${(y.payout_fraction * 100).toFixed(0)}%`, "Index rain"];
          }}
          labelFormatter={(y) => `Season ${y}`}
        />
        <ReferenceLine y={trigger} stroke={C.paid} label={{ value: "trigger", position: "insideTopRight", fontSize: 11, fill: C.paid }} />
        <ReferenceLine y={exit} stroke={C.loss} strokeDasharray="5 4"
          label={{ value: "full payout", position: "insideBottomRight", fontSize: 11, fill: C.loss }} />
        <Bar dataKey="index_rain_mm" isAnimationActive={false}>
          {years.map((y) => <Cell key={y.year} fill={colour(y)} />)}
        </Bar>
      </BarChart>
    </Frame>
  );
}

export const legend = C;
