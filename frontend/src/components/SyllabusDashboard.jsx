import React from 'react';
import { BookOpen, AlertTriangle, CheckCircle, Info } from 'lucide-react';

const SyllabusDashboard = ({ data }) => {
    if (!data) return null;

    const { assignments, policies, raw_omniscient_json, analysis_duration_seconds } = data;

    // Helper to get badge color based on type
    const getStatusBadge = (type) => {
        switch (type) {
            case 'strictly_mandatory':
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-900/30 text-red-400">Mandatory</span>;
            case 'external_transfer':
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-900/30 text-blue-400">Transferable</span>;
            case 'internal_drop':
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-900/30 text-emerald-400">Drop Rule</span>;
            case 'standard_graded':
            default:
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-400">Standard</span>;
        }
    };

    const handleDownloadRaw = () => {
        if (!raw_omniscient_json) {
            console.warn("No raw JSON data available to download.");
            alert("No raw analysis data available.");
            return;
        }

        const jsonString = JSON.stringify(raw_omniscient_json, null, 2);
        const blob = new Blob([jsonString], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "syllabus_analysis_raw.json";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in">

            {/* Course Breakdown */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                <div className="p-6 border-b border-slate-700 flex justify-between items-center">
                    <div>
                        <h3 className="text-lg font-semibold text-white flex items-center">
                            <BookOpen className="w-5 h-5 mr-2 text-blue-400" />
                            Course Breakdown
                            {analysis_duration_seconds && (
                                <span className="ml-3 text-xs font-normal text-slate-400 bg-slate-700/50 px-2 py-0.5 rounded-full border border-slate-600">
                                    {analysis_duration_seconds}s
                                </span>
                            )}
                        </h3>
                        <p className="text-slate-400 text-sm mt-1">
                            Detailed analysis of grading components and policies.
                        </p>
                    </div>
                    <button
                        onClick={handleDownloadRaw}
                        className="text-sm px-3 py-1.5 rounded-md text-blue-400 hover:text-blue-300 border border-blue-400/30 hover:bg-blue-400/10 transition-colors"
                    >
                        Download Raw Analysis (JSON)
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-900/50 text-slate-400 text-sm uppercase">
                            <tr>
                                <th className="px-6 py-4 font-medium">Assignment</th>
                                <th className="px-6 py-4 font-medium">Weight</th>
                                <th className="px-6 py-4 font-medium">Due Date</th>
                                <th className="px-6 py-4 font-medium">Category</th>
                                <th className="px-6 py-4 font-medium">Rules / Evidence</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                            {assignments?.map((item, index) => (
                                <tr key={index} className="hover:bg-slate-700/30 transition-colors">
                                    <td className="px-6 py-4 text-white font-medium">{item.name}</td>
                                    <td className="px-6 py-4 text-slate-300">{item.weight}%</td>
                                    <td className="px-6 py-4 text-slate-300 text-sm">
                                        {item.due_date ? item.due_date : "-"}
                                    </td>
                                    <td className="px-6 py-4">
                                        {getStatusBadge(item.type)}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-400">
                                        {item.evidence}
                                        {item.details && Object.keys(item.details).length > 0 && (
                                            <div className="mt-1 text-xs text-slate-500">
                                                {JSON.stringify(item.details).replace(/[{"}]/g, '').replace(/,/g, ', ')}
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Policies */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Info className="w-5 h-5 mr-2 text-yellow-400" />
                    Extracted Policies
                </h3>
                <div className="grid gap-4">
                    {policies?.map((policy, index) => (
                        <div
                            key={index}
                            className="p-4 rounded-lg border bg-slate-700/30 border-slate-600"
                        >
                            <div className="flex items-start">
                                <div className="w-2 h-2 rounded-full bg-slate-400 mt-2 mr-3 flex-shrink-0" />
                                <p className="text-sm text-slate-300">
                                    {policy}
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
