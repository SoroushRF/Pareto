import React from 'react';
import { BookOpen, AlertTriangle, CheckCircle, Info, Clock } from 'lucide-react'; // Added Clock

const SyllabusDashboard = ({ data }) => {
    if (!data) return null;

    const { assignments, policies, raw_omniscient_json, analysis_duration } = data;

    // Helper to get badge color based on type
    const getStatusBadge = (type) => {
        switch (type) {
            case 'strictly_mandatory':
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-100 dark:border-red-800/50">Mandatory</span>;
            case 'external_transfer':
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-100 dark:border-blue-800/50">Transferable</span>;
            case 'internal_drop':
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/50">Partial</span>;
            case 'standard_graded':
            default:
                return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-200 dark:border-slate-700">Standard</span>;
        }
    };

    const handleDownloadRaw = () => {
        if (!raw_omniscient_json) {
            console.warn("No raw JSON data available to download.");
            alert("No raw analysis data available.");
            return;
        }

        // 1. Get Filename logic
        // Try to get the original filename from the extracted metadata
        let originalName = raw_omniscient_json.syllabus_metadata?.source_file_name || "syllabus";
        
        // Clean it: Remove .pdf extension if present
        // Regex to remove the last dot and everything after it (e.g. .pdf, .png, .txt)
originalName = originalName.replace(/\.[^/.]+$/, "");
        
        // Get Today's Date in YYYY-MM-DD format
        const dateStr = new Date().toISOString().split('T')[0];
        
        // Create new name: [filename]_analysis_[date].json 
        const downloadName = `${originalName}_analysis_${dateStr}.json`;

        // 2. Create and Trigger Download
        const jsonString = JSON.stringify(raw_omniscient_json, null, 2);
        const blob = new Blob([jsonString], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = downloadName; // Use the dynamic name with date
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in">

            {/* Course Breakdown */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm transition-colors duration-300">
                <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center bg-white dark:bg-slate-800/50">
                    <div>
                        <div className="flex items-center gap-3">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center">
                                <BookOpen className="w-5 h-5 mr-3 text-blue-600 dark:text-blue-500" />
                                Course Breakdown
                            </h3>
                            
                            {/* New Time Badge */}
                            {analysis_duration && (
                                <span className="flex items-center px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600">
                                    <Clock className="w-3 h-3 mr-1" />
                                    {analysis_duration}s
                                </span>
                            )}
                        </div>
                        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 font-medium">
                            Detailed analysis of grading components and policies.
                        </p>
                    </div>
                    <button
                        onClick={handleDownloadRaw}
                        className="text-sm font-bold px-4 py-2 rounded-xl text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-all active:scale-95"
                    >
                        Download Raw Analysis
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50/80 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-widest font-bold">
                            <tr>
                                <th className="px-6 py-4">Assignment</th>
                                <th className="px-6 py-4">Weight</th>
                                <th className="px-6 py-4">Due Date</th>
                                <th className="px-6 py-4">Category</th>
                                <th className="px-6 py-4">Rules / Evidence</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                            {assignments?.map((item, index) => (
                                <tr key={index} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30 transition-colors">
                                    <td className="px-6 py-5 text-slate-900 dark:text-white font-bold">{item.name}</td>
                                    <td className="px-6 py-5 text-slate-700 dark:text-slate-300 font-medium">{item.weight}%</td>
                                    <td className="px-6 py-5 text-slate-600 dark:text-slate-400 text-sm font-medium">
                                        {item.due_date ? item.due_date : "-"}
                                    </td>
                                    <td className="px-6 py-5">
                                        {getStatusBadge(item.type)}
                                    </td>
                                    <td className="px-6 py-5 text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                        {item.evidence}
                                        {item.details && Object.keys(item.details).length > 0 && (
                                            <div className="mt-1.5 text-xs text-slate-400 dark:text-slate-500 font-normal">
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
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 shadow-sm transition-colors duration-300">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-6 flex items-center">
                    <Info className="w-5 h-5 mr-3 text-blue-600 dark:text-blue-500" />
                    Extracted Policies
                </h3>
                <div className="grid gap-4">
                    {policies?.map((policy, index) => (
                        <div
                            key={index}
                            className="p-5 rounded-xl border bg-slate-50/50 dark:bg-slate-900/30 border-slate-100 dark:border-slate-700 hover:border-blue-100 dark:hover:border-blue-900/50 transition-colors"
                        >
                            <div className="flex items-start">
                                <div className="w-2 h-2 rounded-full bg-blue-400 dark:bg-blue-600 mt-2 mr-4 flex-shrink-0" />
                                <p className="text-sm text-slate-700 dark:text-slate-300 font-medium leading-relaxed">
                                    {policy}
                                </p>
                            </div>
                        </div>
                    ))}
                    {(!policies || policies.length === 0) && (
                        <p className="text-slate-400 dark:text-slate-500 italic">No specific policies detected.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SyllabusDashboard;
