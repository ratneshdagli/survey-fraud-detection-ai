import { useState, useEffect } from 'react';
import { api } from '../api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function CrossCallHeatmap() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getHeatmap()
      .then(res => {
        // Sort by date ascending
        const sorted = res.sort((a, b) => new Date(a.date) - new Date(b.date));
        setData(sorted);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-[200px] flex items-center justify-center text-gray-400 text-sm animate-pulse">Loading Heatmap...</div>;
  if (error) return <div className="h-[200px] flex items-center justify-center text-red-500 text-sm">Failed: {error}</div>;
  if (data.length === 0) return <div className="h-[200px] flex items-center justify-center text-gray-400 text-sm">No timeline data yet</div>;

  return (
    <div className="h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorFraud" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis 
            dataKey="date" 
            tickFormatter={(val) => {
              const d = new Date(val);
              return `${d.getDate()}/${d.getMonth()+1}`;
            }}
            tick={{ fontSize: 11, fill: '#64748b' }} 
            axisLine={false}
            tickLine={false}
            dy={10}
          />
          <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            labelFormatter={(label) => new Date(label).toLocaleDateString()}
          />
          <Area type="monotone" dataKey="total_calls" name="Total Calls" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorTotal)" />
          <Area type="monotone" dataKey="fraud_calls" name="Fraud Flagged" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorFraud)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
