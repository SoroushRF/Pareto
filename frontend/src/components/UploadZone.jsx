import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Loader2, AlertCircle } from 'lucide-react';

const UploadZone = ({ onAnalysisComplete }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [targetGrade, setTargetGrade] = useState(80);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('target_grade', targetGrade);

        try {
            const response = await axios.post('http://localhost:8000/analyze', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            onAnalysisComplete(response.data);
        } catch (err) {
            console.error("Upload failed:", err);
            setError("Failed to analyze syllabus. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-xl mx-auto">
            <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-blue-500 transition-colors bg-slate-800/50">
                {loading ? (
                    <div className="flex flex-col items-center py-8">
                        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                        <p className="text-lg font-medium text-blue-400">Analyzing your fate...</p>
                        <p className="text-sm text-slate-400 mt-2">Calculating the optimal path to {targetGrade}%...</p>
                    </div>
                ) : (
                    <>
                        <div className="flex justify-center mb-4">
                            <div className="p-4 bg-slate-700 rounded-full">
                                <Upload className="w-8 h-8 text-blue-400" />
                            </div>
                        </div>
                        <h3 className="text-xl font-semibold text-white mb-2">Upload Syllabus</h3>
                        <p className="text-slate-400 mb-6">Drag and drop your PDF here, or click to browse</p>

                        <div className="mb-8 max-w-xs mx-auto">
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Desired Grade: <span className="text-blue-400 font-bold">{targetGrade}%</span>
                            </label>
                            <input
                                type="range"
                                min="50"
                                max="100"
                                value={targetGrade}
                                onChange={(e) => setTargetGrade(e.target.value)}
                                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                            />
                            <div className="flex justify-between text-xs text-slate-500 mt-1">
                                <span>50%</span>
                                <span>100%</span>
                            </div>
                        </div>

                        <label className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg cursor-pointer transition-colors">
                            <span>Select PDF</span>
                            <input
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                onChange={handleFileUpload}
                            />
                        </label>
                    </>
                )}
            </div>

            {error && (
                <div className="mt-4 p-4 bg-red-900/20 border border-red-800 rounded-lg flex items-center text-red-400">
                    <AlertCircle className="w-5 h-5 mr-2" />
                    {error}
                </div>
            )}
        </div>
    );
};

export default UploadZone;
