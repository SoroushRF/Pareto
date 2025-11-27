import React, { useState, useCallback, useEffect, useRef } from 'react';
import axios from 'axios';
import { Upload, Loader2, AlertCircle, FileText } from 'lucide-react';

const UploadZone = ({ onAnalysisComplete }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    
    // REF: Store the controller so we can cancel it anytime
    const abortControllerRef = useRef(null);

    // CLEANUP: Cancel request if component unmounts (user leaves/refreshes)
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    const processFile = async (file) => {
        if (!file) return;

        // Cancel any previous pending request before starting a new one
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // Create new controller for this specific request
        abortControllerRef.current = new AbortController();

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post('http://localhost:8000/analyze', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                // LINK: Connect the signal to Axios
                signal: abortControllerRef.current.signal
            });
            
            onAnalysisComplete({ ...response.data, filename: file.name });
        } catch (err) {
            // IGNORE cancellations (don't show red error box)
            if (axios.isCancel(err)) {
                console.log('Request canceled by user/unmount.');
                return;
            }

            console.error("Upload failed:", err);
            const serverError = err.response?.data?.error;
            setError(serverError || "Failed to analyze syllabus. Please try again.");
        } finally {
            // Only turn off loading if we weren't canceled (prevents UI flicker)
            if (!axios.isCancel(err)) {
                setLoading(false);
            }
            setIsDragging(false);
            abortControllerRef.current = null;
        }
    };

    const handleFileInput = (event) => {
        const file = event.target.files[0];
        processFile(file);
    };

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            processFile(files[0]);
        }
    }, []);

    return (
        <div className="w-full max-w-xl mx-auto">
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                    border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ease-in-out
                    ${isDragging 
                        ? 'border-blue-500 bg-blue-500/10 scale-[1.02]' 
                        : 'border-slate-700 bg-slate-800/50 hover:border-blue-500/50 hover:bg-slate-800'
                    }
                `}
            >
                {loading ? (
                    <div className="flex flex-col items-center py-8 animate-pulse">
                        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
                        <p className="text-lg font-medium text-blue-400">Analyzing Syllabus...</p>
                        <p className="text-sm text-slate-400 mt-2">Extracting grading rules, dates, and policies...</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center">
                        <div className={`p-4 rounded-full mb-4 transition-colors ${isDragging ? 'bg-blue-500/20' : 'bg-slate-700'}`}>
                            {isDragging ? (
                                <FileText className="w-8 h-8 text-blue-400 animate-bounce" />
                            ) : (
                                <Upload className="w-8 h-8 text-blue-400" />
                            )}
                        </div>
                        
                        <h3 className="text-xl font-semibold text-white mb-2">
                            {isDragging ? "Drop it here!" : "Upload Syllabus"}
                        </h3>
                        
                        <p className="text-slate-400 mb-6 max-w-xs mx-auto">
                            Drag and drop your PDF, Image, or Text file here, or click to browse
                        </p>

                        <label className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg cursor-pointer transition-transform active:scale-95 shadow-lg shadow-blue-900/20">
                            <span>Select File</span>
                            <input
                                type="file"
                                accept=".pdf,.png,.jpg,.jpeg,.heic,.txt,.md,application/pdf,image/*,text/plain,text/markdown"
                                className="hidden"
                                onChange={handleFileInput}
                            />
                        </label>
                        
                        <p className="mt-4 text-xs text-slate-500">
                            Supports PDF, PNG, JPG, TXT, MD
                        </p>
                    </div>
                )}
            </div>

            {error && (
                <div className="mt-4 p-4 bg-red-900/20 border border-red-800 rounded-lg flex items-start text-red-400 animate-fade-in">
                    <AlertCircle className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5" />
                    <div className="text-sm">{error}</div>
                </div>
            )}
        </div>
    );
};

export default UploadZone;