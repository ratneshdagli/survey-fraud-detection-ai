import { useState, useEffect } from 'react';
import { api } from '../api';

export default function AgentLeaderboard() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getLeaderboard()
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-center text-gray-400 text-sm animate-pulse">Loading Leaderboard...</div>;
  if (error) return <div className="p-6 text-center text-red-500 text-sm">Failed: {error}</div>;
  if (data.length === 0) return <div className="p-6 text-center text-gray-400 text-sm">No agent data yet</div>;

  return (
    <div className="glass-card-solid overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-gray-100/50 bg-white/50 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider flex items-center gap-2">
          🏆 Agent Risk Leaderboard
        </h3>
      </div>
      
      <div className="overflow-x-auto flex-1 h-[250px] overflow-y-auto custom-scrollbar p-2">
        <table className="w-full text-left border-collapse min-w-[500px]">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Agent</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center">Calls</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center">Fraud Issues</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase text-center">Avg Risk Score</th>
              <th className="px-4 py-3 text-xs font-bold text-gray-700 uppercase tracking-wider text-right">Composite Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((agent, i) => {
              const severityBg = 
                agent.composite_risk_score >= 8 ? "bg-red-50 hover:bg-red-100/70" :
                agent.composite_risk_score >= 5 ? "bg-amber-50 hover:bg-amber-100/70" :
                "hover:bg-gray-50/50";
              const idxStyle = i === 0 ? "bg-red-600 text-white w-6 h-6 rounded-full inline-flex items-center justify-center text-xs ml-2" : "text-gray-400 w-6 text-center inline-block text-xs ml-2";

              return (
                <tr key={agent.surveyor_name || `unknown-${i}`} className={`transition-colors ${severityBg}`}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                    {agent.surveyor_name || "Unknown"} <span className={idxStyle}>{i + 1}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-center font-mono">{agent.total_calls}</td>
                  <td className="px-4 py-3 text-sm text-center">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      agent.fraud_rate > 50 ? 'bg-red-100 text-red-700' :
                      agent.fraud_rate > 20 ? 'bg-amber-100 text-amber-700' :
                      agent.fraud_rate === 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {agent.fraud_rate}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-center font-mono">{agent.avg_risk_score}/10</td>
                  <td className="px-4 py-3 text-sm text-right pr-6">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${agent.composite_risk_score >= 7 ? 'bg-red-500' : agent.composite_risk_score >= 5 ? 'bg-amber-500' : 'bg-emerald-500'}`} 
                          style={{ width: `${Math.min(100, agent.composite_risk_score * 10)}%` }} 
                        />
                      </div>
                      <span className="font-bold text-gray-800 tabular-nums w-8">
                        {agent.composite_risk_score.toFixed(1)}
                      </span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
