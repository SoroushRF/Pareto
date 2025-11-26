import React from 'react';
import { BookOpen, AlertTriangle, CheckCircle } from 'lucide-react';

const SyllabusDashboard = ({ data }) => {
    if (!data) return null;

    const { total_points, assignments, policies } = data;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in">
            {/* Header Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <p className="text-slate-400 text-sm font-medium">Total Points</p>
                    <p className="text-3xl font-bold text-white mt-1">{total_points}</p>
                </div>
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <p className="text-slate-400 text-sm font-medium">Assignments</p>
                    <p className="text-3xl font-bold text-blue-400 mt-1">{assignments?.length || 0}</p>
                </div>
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
                    <p className="text-slate-400 text-sm font-medium">Policies Found</p>
                    <p className="text-3xl font-bold text-emerald-400 mt-1">{policies?.length || 0}</p>
                </div>
            </div>

            {/* Assignments Breakdown */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                <div className="p-6 border-b border-slate-700">
                    <h3 className="text-lg font-semibold text-white flex items-center">
                        <BookOpen className="w-5 h-5 mr-2 text-blue-400" />
                        Grading Breakdown
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-900/50 text-slate-400 text-sm uppercase">
                            <tr>
                                <th className="px-6 py-4 font-medium">Assignment</th>
                                <th className="px-6 py-4 font-medium">Weight</th>
                                <th className="px-6 py-4 font-medium">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                            {assignments?.map((item, index) => (
                                <tr key={index} className="hover:bg-slate-700/30 transition-colors">
                                    <td className="px-6 py-4 text-white font-medium">{item.name}</td>
                                    <td className="px-6 py-4 text-slate-300">{item.weight}%</td>
                                    <td className="px-6 py-4">
                                        {item.mandatory ? (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-900/30 text-red-400">
                                                Mandatory
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-400">
                                                Optional
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Strategy Section */}
            {data.strategy && (
                <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                    <div className="p-6 border-b border-slate-700">
                        <h3 className="text-lg font-semibold text-white flex items-center">
                            <div className="w-2 h-2 rounded-full bg-blue-500 mr-2 animate-pulse"></div>
                            Pareto Plan: Target {data.strategy.target_grade}%
                        </h3>
                        <p className="text-slate-400 text-sm mt-1">{data.strategy.summary}</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-700">
                        {/* Safe to Skip */}
                        <div className="p-6 bg-emerald-900/10">
                            <h4 className="text-emerald-400 font-medium mb-4 flex items-center">
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Safe to Skip (Optional)
                            </h4>
                            <ul className="space-y-3">
                                {data.strategy.safe_to_skip?.map((item, idx) => (
                                    <li key={idx} className="flex items-start text-sm">
                                        <span className="text-slate-300 font-medium mr-2">• {item.name}:</span>
                                        <span className="text-slate-500">{item.reason}</span>
                                    </li>
                                ))}
                                {(!data.strategy.safe_to_skip || data.strategy.safe_to_skip.length === 0) && (
                                    <li className="text-slate-500 italic text-sm">No assignments can be safely skipped.</li>
                                )}
                            </ul>
                        </div>

                        {/* Must Do */}
                        <div className="p-6 bg-red-900/10">
                            <h4 className="text-red-400 font-medium mb-4 flex items-center">
                                <AlertTriangle className="w-4 h-4 mr-2" />
                                Critical (Must Do)
                            </h4>
                            <ul className="space-y-3">
                                {data.strategy.must_do?.map((item, idx) => (
                                    <li key={idx} className="flex items-start text-sm">
                                        <span className="text-slate-300 font-medium mr-2">• {item.name}:</span>
                                        <span className="text-slate-500">{item.reason}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {/* Policies */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <AlertTriangle className="w-5 h-5 mr-2 text-yellow-400" />
                    Important Policies
                </h3>
                <div className="grid gap-4">
                    {policies?.map((policy, index) => (
                        <div
                            key={index}
                            className={`p-4 rounded-lg border ${policy.type === 'drop_lowest'
                                ? 'bg-yellow-900/20 border-yellow-700/50'
                                : 'bg-slate-700/30 border-slate-600'
                                }`}
                        >
                            <div className="flex items-start">
                                {policy.type === 'drop_lowest' ? (
                                    <CheckCircle className="w-5 h-5 text-yellow-400 mt-0.5 mr-3 flex-shrink-0" />
                                ) : (
                                    <div className="w-2 h-2 rounded-full bg-slate-400 mt-2 mr-3 flex-shrink-0" />
                                )}
                                <p className={`text-sm ${policy.type === 'drop_lowest' ? 'text-yellow-200' : 'text-slate-300'
                                    }`}>
                                    {policy.rule}
                                </p>
                            </div>
                        </div>
                    ))}
                    {(!policies || policies.length === 0) && (
                        <p className="text-slate-500 italic">No specific policies detected.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SyllabusDashboard;
