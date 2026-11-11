"use client";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const AXIS = { fontSize: 11, fill: "#5B6B7F" };
const TT = { contentStyle: { borderRadius: 7, border: "1px solid #D7DEE8", fontSize: 12, boxShadow: "0 4px 14px rgba(11,31,58,.08)" } };

export function VolumeChart({ data }: { data: { date: string; screenings: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id="vol" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#1F6FB2" stopOpacity={0.22} />
            <stop offset="100%" stopColor="#1F6FB2" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#EEF2F7" vertical={false} />
        <XAxis dataKey="date" tick={AXIS} tickLine={false} axisLine={false} minTickGap={28}
          tickFormatter={(d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} />
        <YAxis allowDecimals={false} tick={AXIS} tickLine={false} axisLine={false} />
        <Tooltip {...TT} labelFormatter={(d: any) => new Date(d).toLocaleDateString("en-IN", { dateStyle: "medium" })} />
        <Area type="monotone" dataKey="screenings" name="Screenings" stroke="#1F6FB2" strokeWidth={2} fill="url(#vol)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function HBars({ data, colors }: { data: { name: string; value: number }[]; colors?: string[] }) {
  if (!data.length || data.every((d) => !d.value)) return <p className="py-10 text-center text-sm text-slate">No data in this period yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={Math.max(120, data.length * 38)}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }}>
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis type="category" dataKey="name" width={150} tick={AXIS} tickLine={false} axisLine={false} />
        <Tooltip {...TT} cursor={{ fill: "#F3F6FA" }} />
        <Bar dataKey="value" name="Count" radius={[0, 4, 4, 0]} barSize={18} label={{ position: "right", fontSize: 11, fill: "#14202E" }}>
          {data.map((_, i) => <Cell key={i} fill={colors?.[i % colors.length] ?? "#3E8E8A"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
