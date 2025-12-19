import React, { useState, useCallback, useEffect, useRef } from 'react';
import axios from 'axios';
import { Upload, Loader2, AlertCircle, FileText, XCircle, RefreshCcw } from 'lucide-react';

const UploadZone = ({ onAnalysisComplete }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    
    // REF: Store the controller so we can cancel it anytime
    const abortControllerRef = useRef(null);

    // Allowed Extensions for Validation
    const ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'heic', 'txt', 'md', 'docx'];

    // CLEANUP: Cancel request if component unmounts
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    const validateFile = (file) => {
        const extension = file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(extension)) {
            return {
                valid: false,
                message: `Unsupported format (.${extension}). Please upload PDF, Image, or Text.`
            };
        }
        return { valid: true };
    };

    const processFile = async (file) => {
        if (!file) return;

        // 1. VALIDATION STEP
        const validation = validateFile(file);
        if (!validation.valid) {
            setError(validation.message);
            return; // Stop here, don't send to backend
        }

        // Cancel any previous pending request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();
        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post('http://localhost:8000/analyze', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                signal: abortControllerRef.current.signal
            });
            
            onAnalysisComplete({ ...response.data, filename: file.name });
        } catch (err) {
            if (axios.isCancel(err)) {
                console.log('Request canceled.');
                return;
            }
            console.error("Upload failed:", err);
            setError("Failed to analyze syllabus. Please try again.");
        } finally {
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

    const resetUpload = () => {
        setError(null);
        setLoading(false);
    };

    // --- DYNAMIC STYLES ---
    // If Error: Red. If Dragging: Blue. Else: Slate.
    let borderColor = 'border-slate-200 dark:border-slate-800';
    let bgColor = 'bg-slate-50 dark:bg-slate-800/40';
    
    if (error) {
        borderColor = 'border-red-200 dark:border-red-900/50';
        bgColor = 'bg-red-50 dark:bg-red-900/10';
    } else if (isDragging) {
        borderColor = 'border-blue-400 dark:border-blue-500';
        bgColor = 'bg-blue-50 dark:bg-blue-500/10';
    }

    const fileInputRef = useRef(null);

    const triggerFileInput = () => {
        if (!error && !loading && fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    return (
        <div className="w-full max-w-xl mx-auto">
            <div
                onClick={triggerFileInput}
                onDragOver={!error && !loading ? handleDragOver : undefined}
                onDragLeave={!error && !loading ? handleDragLeave : undefined}
                onDrop={!error && !loading ? handleDrop : undefined}
                className={`
                    border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-300 ease-in-out relative
                    ${borderColor} ${bgColor}
                    ${!error && !loading ? 'hover:border-blue-300 dark:hover:border-blue-700 hover:bg-slate-100/50 dark:hover:bg-slate-800/60 cursor-pointer' : ''}
                    ${isDragging ? 'scale-[1.01] shadow-xl shadow-blue-500/5 dark:shadow-blue-500/10' : ''}
                `}
            >
                {/* Hidden File Input accessible via ref */}
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.heic,.txt,.md,.docx,application/pdf,image/*,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    className="hidden"
                    onChange={handleFileInput}
                />

                {/* STATE 1: ERROR VIEW */}
                {error ? (
                    <div className="flex flex-col items-center py-4 animate-fade-in">
                        <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
                            <XCircle className="w-10 h-10 text-red-600 dark:text-red-500" />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                            Unable to Upload
                        </h3>
                        <p className="text-slate-600 dark:text-slate-400 mb-6 max-w-xs">
                            {error}
                        </p>
                        <button 
                            onClick={(e) => { e.stopPropagation(); resetUpload(); }}
                            className="inline-flex items-center px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl transition-all shadow-md hover:shadow-lg active:scale-95"
                        >
                            <RefreshCcw className="w-4 h-4 mr-2" />
                            Try Another File
                        </button>
                    </div>
                ) : loading ? (
                    /* STATE 2: LOADING VIEW */
                    <div className="flex flex-col items-center py-8">
                        <Loader2 className="w-12 h-12 text-blue-600 dark:text-blue-500 animate-spin mb-4" />
                        <p className="text-lg font-bold text-slate-900 dark:text-white">Analyzing Syllabus...</p>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">Extracting grading rules, dates, and policies...</p>
                    </div>
                ) : (
                    /* STATE 3: DEFAULT UPLOAD VIEW */
                    <div className="flex flex-col items-center">
                        <div className={`p-5 rounded-3xl mb-4 transition-colors ${isDragging ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-slate-200/50 dark:bg-slate-800'}`}>
                            {isDragging ? (
                                <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-bounce" />
                            ) : (
                                <Upload className="w-8 h-8 text-blue-600 dark:text-blue-500" />
                            )}
                        </div>
                        
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                            {isDragging ? "Drop your syllabus here" : "Upload Syllabus"}
                        </h3>
                        
                        <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-xs mx-auto leading-relaxed">
                            Drag and drop your PDF, Image, or Text file here, or click anywhere to browse
                        </p>

                        <div className="inline-flex items-center px-8 py-3.5 bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white font-bold rounded-xl cursor-pointer transition-all active:scale-95 shadow-lg shadow-blue-500/20 hover:shadow-xl hover:shadow-blue-500/30 dark:shadow-blue-900/40">
                            Select File
                        </div>
                        
                        <p className="mt-6 text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                            Supports PDF, DOCX, PNG, JPG, TXT, MD
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default UploadZone;