import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import AgentLeaderboard from './AgentLeaderboard';
import CrossCallHeatmap from './CrossCallHeatmap';

/**
 * Z-AUDIT Dashboard Component
 * Stats cards, fraud chart, filters, and records table.
 */

const FRAUD_COLORS = {
  fake_form: '#dc2626',
  mimicry: '#ea580c',
  force_survey: '#d97706',
  clean: '#16a34a',
};

const FRAUD_LABELS = {
  fake_form: 'Fake Form',
  mimicry: 'Mimicry',
  force_survey: 'Force Survey',
  clean: 'Clean',
};

const FRAUD_EMOJI = {
  fake_form: '👻',
  mimicry: '🎭',
  force_survey: '💪',
  clean: '✅',
};

function getScoreColor(score) {
  if (score >= 7) return 'text-emerald-600';
  if (score >= 5) return 'text-amber-600';
  return 'text-red-600';
}

function getScoreBg(score) {
  if (score >= 7) return 'bg-emerald-50';
  if (score >= 5) return 'bg-amber-50';
  return 'bg-red-50';
}

function formatDuration(seconds) {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

export default function Dashboard({
  stats,
  records,
  totalRecords,
  totalPages,
  page,
  loading,
  error,
  fraudFilter,
  minScore,
  searchQuery,
  onFilterChange,
  onMinScoreChange,
  onSearchChange,
  onPageChange,
  onRecordClick,
  onDelete,
}) {
  // Chart data from stats
  const chartData = useMemo(() => {
    if (!stats?.fraud_breakdown) return [];
    return Object.entries(stats.fraud_breakdown).map(([key, value]) => ({
      name: FRAUD_LABELS[key] || key,
      count: value,
      fill: FRAUD_COLORS[key] || '#94a3b8',
    }));
  }, [stats]);

  return (
    <div className="space-y-6">
      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-5 py-3 rounded-xl flex items-center gap-3">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {/* =========== STATS CARDS =========== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Calls */}
        <div className="stat-card" style={{ background: 'linear-gradient(135deg, #1e40af, #3b82f6)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-blue-200 text-sm font-medium">Total Calls Audited</span>
            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
            </div>
          </div>
          <p className="text-4xl font-extrabold">{stats?.total_calls ?? '—'}</p>
        </div>

        {/* Fraud Detected */}
        <div className="stat-card" style={{ background: 'linear-gradient(135deg, #991b1b, #dc2626)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-red-200 text-sm font-medium">Fraud Detected</span>
            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>
          <p className="text-4xl font-extrabold">{stats?.fraud_detected ?? '—'}</p>
          <p className="text-red-200 text-sm mt-1">{stats?.fraud_percentage ?? 0}% of total</p>
        </div>

        {/* Avg Quality Score */}
        <div className="stat-card" style={{ background: `linear-gradient(135deg, ${(stats?.avg_quality_score ?? 5) >= 7 ? '#065f46, #16a34a' : (stats?.avg_quality_score ?? 5) >= 5 ? '#92400e, #d97706' : '#991b1b, #dc2626'})` }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-white/70 text-sm font-medium">Avg Quality Score</span>
            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </div>
          </div>
          <p className="text-4xl font-extrabold">{stats?.avg_quality_score ?? '—'}<span className="text-lg font-medium opacity-70">/10</span></p>
        </div>

        {/* Clean Calls */}
        <div className="stat-card" style={{ background: 'linear-gradient(135deg, #065f46, #16a34a)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-emerald-200 text-sm font-medium">Clean Calls</span>
            <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <p className="text-4xl font-extrabold">{stats?.clean_calls ?? '—'}</p>
          <p className="text-emerald-200 text-sm mt-1">{stats?.clean_percentage ?? 0}% of total</p>
        </div>
      </div>

      {/* =========== CHART + FILTERS ROW =========== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Fraud Breakdown Chart */}
        <div className="glass-card-solid p-6 lg:col-span-1">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Fraud Breakdown</h3>
          <div className="h-[200px]">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis type="category" dataKey="name" width={95} tick={{ fontSize: 12, fill: '#334155' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 10px 25px rgba(0,0,0,0.08)' }}
                  />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={28}>
                    {chartData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">No data yet</div>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="glass-card-solid p-6 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Filters</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Fraud Type */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1.5 block">Fraud Type</label>
              <select
                value={fraudFilter}
                onChange={(e) => { onFilterChange(e.target.value); onPageChange(1); }}
                className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Types</option>
                <option value="fake_form">👻 Fake Form</option>
                <option value="mimicry">🎭 Mimicry</option>
                <option value="force_survey">💪 Force Survey</option>
                <option value="clean">✅ Clean</option>
              </select>
            </div>

            {/* Min Score */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1.5 block">
                Min Quality Score: <span className="text-blue-600 font-bold">{minScore}</span>
              </label>
              <input
                type="range"
                min="0"
                max="10"
                step="0.5"
                value={minScore}
                onChange={(e) => { onMinScoreChange(Number(e.target.value)); onPageChange(1); }}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 mt-2"
              />
              <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                <span>0</span><span>5</span><span>10</span>
              </div>
            </div>

            {/* Search */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1.5 block">Search UID / Surveyor</label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => { onSearchChange(e.target.value); onPageChange(1); }}
                  placeholder="e.g. 111379 or Maroti"
                  className="w-full pl-9 pr-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* =========== LEADERBOARD + HEATMAP ROW =========== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 h-[320px]">
          <AgentLeaderboard />
        </div>
        <div className="lg:col-span-1 glass-card-solid p-4 flex flex-col h-[320px]">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex-shrink-0">
            Fraud Occurrence Trend
          </h3>
          <div className="flex-1 min-h-0">
            <CrossCallHeatmap />
          </div>
        </div>
      </div>

      {/* =========== RECORDS TABLE =========== */}
      <div className="glass-card-solid overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            Audit Records <span className="text-blue-600">({totalRecords})</span>
          </h3>
          {loading && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <div className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
              Loading...
            </div>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50/80">
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">UID</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Surveyor</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Duration</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Fraud Type</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Quality</th>
                <th className="text-center px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {records.length === 0 && !loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-16">
                    <div className="text-gray-400">
                      <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                      </svg>
                      <p className="font-medium">No records found</p>
                      <p className="text-sm mt-1">Upload audio files or seed the database to get started.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr
                    key={record.uid}
                    className="table-row-hover group"
                    onClick={() => onRecordClick(record)}
                  >
                    <td className="px-6 py-4">
                      <span className="font-mono font-bold text-blue-700 text-sm">{record.uid}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm font-medium text-gray-800 truncate block max-w-[200px]">
                        {record.surveyor_name || '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">{record.survey_date || '—'}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600 font-mono">{formatDuration(record.time_difference_seconds)}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`badge badge-${record.fraud_type}`}>
                        {FRAUD_EMOJI[record.fraud_type]} {FRAUD_LABELS[record.fraud_type] || record.fraud_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-sm font-bold ${getScoreColor(record.quality_score)} ${getScoreBg(record.quality_score)}`}>
                        {record.quality_score?.toFixed(1) ?? '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={(e) => { e.stopPropagation(); onRecordClick(record); }}
                          className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                          title="View Details"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); onDelete(record.uid); }}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                          title="Delete"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Page <span className="font-semibold text-gray-700">{page}</span> of{' '}
              <span className="font-semibold text-gray-700">{totalPages}</span>
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => onPageChange(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="px-4 py-2 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => onPageChange(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="px-4 py-2 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
