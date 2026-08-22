import React, { useState, useRef, useEffect } from 'react';
import { 
  Heart, Sun, Moon, LogOut, FileText, Mic, Image, 
  Trash2, Play, Pause, RefreshCw, ChevronDown, ChevronUp,
  AlertTriangle, CheckCircle2, HelpCircle, Upload, AlertCircle, FileAudio
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const getExplanationMarkdown = (llmOutput) => {
  if (!llmOutput) return '';
  const lines = llmOutput.split('\n');
  const content = lines.slice(1).join('\n');
  const parts = content.split(/### Suggested Alternatives/i);
  return parts[0].replace(/Explanation:/i, '').trim();
};

const getAlternativesMarkdown = (llmOutput) => {
  if (!llmOutput) return '';
  const parts = llmOutput.split(/### Suggested Alternatives/i);
  if (parts.length < 2) return '';
  const contentAfterHeader = parts[1];
  const warningSplit = contentAfterHeader.split(/### (?:⚠️ )?Important Warning|### (?:⚠️ )?Warning/i);
  return warningSplit[0].trim();
};

export default function Dashboard({ user, onSignOut, theme, toggleTheme }) {
  // Input States
  const [symptoms, setSymptoms] = useState('');
  const [audioClips, setAudioClips] = useState([]); // Array of { id, file, url, name, duration }
  const [imageFile, setImageFile] = useState(null); // File object
  const [imagePreview, setImagePreview] = useState(null); // Data URL

  // Voice Recording States
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);

  // Analysis/Status States
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [collapsedSections, setCollapsedSections] = useState({
    diseases: true,
    drugs: true,
    drug_dict: true,
  });

  // Audio Playback states for clips
  const [playingClipId, setPlayingClipId] = useState(null);
  const activeAudioRef = useRef(null);

  // Cleanup URLs on unmount
  useEffect(() => {
    return () => {
      audioClips.forEach(clip => URL.revokeObjectURL(clip.url));
      if (imagePreview) URL.revokeObjectURL(imagePreview);
    };
  }, []);

  // Timer for voice recording
  useEffect(() => {
    if (isRecording) {
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } else {
      clearInterval(recordingTimerRef.current);
      setRecordingDuration(0);
    }
    return () => clearInterval(recordingTimerRef.current);
  }, [isRecording]);

  // Loading indicator messages
  const loadingSteps = [
    "Uploading data to secure local server...",
    "Transcribing voice recording clips with Whisper...",
    "Running PaddleOCR on medicine label image...",
    "Matching symptoms against local FAISS disease database...",
    "Searching local FAISS drug databases...",
    "Analyzing mismatch & generating RAG suggestions with Mistral...",
  ];

  // Auto-advance loading steps for visual feedback
  useEffect(() => {
    let interval;
    if (isLoading) {
      interval = setInterval(() => {
        setLoadingStep(prev => (prev < loadingSteps.length - 1 ? prev + 1 : prev));
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  // 1. Microphone Live Recording Handler
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const clipId = Date.now();
        const clipName = `Recorded Clip #${audioClips.length + 1}`;
        const newClip = {
          id: clipId,
          file: new File([audioBlob], `recorded_${clipId}.webm`, { type: 'audio/webm' }),
          url: audioUrl,
          name: clipName,
          duration: recordingDuration
        };
        setAudioClips(prev => [...prev, newClip]);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
      setError("Microphone access was denied. Please allow mic permissions or upload files.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // 2. Audio File Upload Handler
  const handleAudioUpload = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    files.forEach((file, index) => {
      const audioUrl = URL.createObjectURL(file);
      const clipId = Date.now() + index;
      const newClip = {
        id: clipId,
        file: file,
        url: audioUrl,
        name: file.name,
        duration: 0 // unknown unless we load metadata, default to 0
      };
      setAudioClips(prev => [...prev, newClip]);
    });
    e.target.value = ''; // Reset input
  };

  const deleteClip = (id) => {
    setAudioClips(prev => {
      const clipToDelete = prev.find(c => c.id === id);
      if (clipToDelete) URL.revokeObjectURL(clipToDelete.url);
      return prev.filter(c => c.id !== id);
    });
    if (playingClipId === id) {
      stopAudioPlayback();
    }
  };

  const togglePlayClip = (clip) => {
    if (playingClipId === clip.id) {
      stopAudioPlayback();
    } else {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
      }
      const audio = new Audio(clip.url);
      activeAudioRef.current = audio;
      audio.onended = () => {
        setPlayingClipId(null);
      };
      audio.play();
      setPlayingClipId(clip.id);
    }
  };

  const stopAudioPlayback = () => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    setPlayingClipId(null);
  };

  // 3. Medicine Image Handlers (Drag & Drop + File Upload)
  const handleImageFile = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please upload a valid image file (PNG/JPG).');
      return;
    }
    setError('');
    setImageFile(file);
    const previewUrl = URL.createObjectURL(file);
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImagePreview(previewUrl);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    handleImageFile(file);
  };

  const removeImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImageFile(null);
    setImagePreview(null);
  };

  // 4. API Core Action Handler
  const handleAnalyze = async () => {
    if (!symptoms.trim() && audioClips.length === 0 && !imageFile) {
      setError("Please provide at least one input: symptoms description, audio recording, or medicine photo.");
      return;
    }

    setError('');
    setIsLoading(true);
    setLoadingStep(0);
    setResult(null);

    // Build Form Data
    const formData = new FormData();
    if (symptoms.trim()) formData.append('text', symptoms.trim());
    if (imageFile) formData.append('image', imageFile);
    
    audioClips.forEach(clip => {
      formData.append('audio', clip.file);
    });

    try {
      const response = await fetch('http://127.0.0.1:8000/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error("API error:", err);
      // Give a detailed error and offer mock fallback
      setError(
        `Failed to reach local MediScanAI server: ${err.message}. ` +
        `Make sure the FastAPI backend is running locally at http://localhost:8000.`
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Fallback / Demo simulation when backend is down
  const handleSimulateMock = () => {
    setError('');
    setIsLoading(true);
    setLoadingStep(0);
    
    // Fake loading delay
    setTimeout(() => {
      const isNotSuitable = symptoms.toLowerCase().includes('cough') || symptoms.toLowerCase().includes('throat') || symptoms.toLowerCase().includes('fever');
      
      const mockResult = {
        "card": {
          "user_text": symptoms || "Patient presents with dry cough and mild evening fever.",
          "ocr_text": imageFile ? "BEPLEX FORTE Multivitamin Tablets - Anglo-French Drugs" : "",
          "llm_output": isNotSuitable 
            ? `Based on the information provided, the medicine identified from the package, which appears to be **Beplex Forte**, is **not suitable** for treating your symptoms of a dry cough and fever.

Explanation:
Beplex Forte is a B-complex vitamin supplement intended to treat nutritional deficiencies. It does not contain any active antitussives (cough suppressants), antipyretics (fever reducers), or antimicrobial agents necessary to treat a respiratory infection. Using it as a primary treatment will not address your symptoms.

### Suggested Alternatives
* **Dextromethorphan**: An oral cough suppressant that works on the brain to decrease the urge to cough. Highly appropriate for a non-productive dry cough.
* **Paracetamol (Acetaminophen)**: A mild analgesic and antipyretic that reduces fever and relieves minor body aches.

### ⚠️ Important Warning
This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition.`
            : `Based on the information provided, the medicine identified from the package, which appears to be **Beplex Forte**, is **suitable** for treating your symptoms of fatigue and vitamin deficiency.

Explanation:
Beplex Forte provides Thiamine, Riboflavin, Niacinamide, and Vitamin C, which assist in metabolism and energy production, addressing signs of B-complex deficiency and general physical fatigue.

### Suggested Alternatives
* **Zincovit**: A popular multivitamin and multimineral tablet that provides essential nutrients including Zinc to support immune health.

### ⚠️ Important Warning
This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition.`,
          "retrieved": {
            "diseases": [
              {
                "key": "respiratory_infection",
                "score": 0.8245,
                "preview": {
                  "disease": "Acute Bronchitis",
                  "symptoms": "dry cough, sore throat, low-grade fever, fatigue"
                }
              }
            ],
            "drugs": [
              {
                "key": "dextromethorphan",
                "score": 0.7912,
                "preview": {
                  "generic_name": "Dextromethorphan HBr",
                  "indications_and_usage": "Temporary relief of coughs due to minor throat irritation"
                }
              },
              {
                "key": "paracetamol",
                "score": 0.7410,
                "preview": {
                  "generic_name": "Paracetamol",
                  "indications_and_usage": "Temporary relief of mild-to-moderate pain and reduction of fever"
                }
              }
            ],
            "drug_dict": [
              {
                "key": "beplex_forte",
                "score": 0.9521,
                "preview": {
                  "brand_name": "Beplex Forte",
                  "generic_name": "Vitamin B-Complex with Vitamin C"
                }
              }
            ]
          }
        }
      };

      setResult(mockResult);
      setIsLoading(false);
    }, 4000);
  };

  // 5. Verdict Classification for Styling
  const getVerdictStyle = (llmText) => {
    if (!llmText) return { type: 'neutral', classes: 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800' };
    const lower = llmText.toLowerCase();
    
    // Look at first 150 chars (verdict section)
    const verdictArea = lower.substring(0, Math.min(250, lower.length));
    
    if (verdictArea.includes('not suitable') || verdictArea.includes('not appropriate') || verdictArea.includes('mismatch')) {
      return { 
        type: 'danger', 
        classes: 'bg-rose-50/70 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/30 text-rose-900 dark:text-rose-200',
        badge: 'bg-rose-600/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/40',
        icon: <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
      };
    }
    if (verdictArea.includes('suitable') || verdictArea.includes('appropriate') || verdictArea.includes('match')) {
      return { 
        type: 'success', 
        classes: 'bg-emerald-50/70 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/30 text-emerald-900 dark:text-emerald-200',
        badge: 'bg-emerald-600/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/40',
        icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
      };
    }
    return { 
      type: 'warning', 
      classes: 'bg-amber-50/70 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/30 text-amber-900 dark:text-amber-200',
      badge: 'bg-amber-600/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900/40',
      icon: <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
    };
  };

  const formatDuration = (sec) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const toggleCollapse = (section) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const cardData = result?.card;
  const verdictInfo = getVerdictStyle(cardData?.llm_output);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 transition-colors duration-300 font-sans">
      
      {/* 1. Header Bar */}
      <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center shadow-md shadow-teal-600/10">
            <Heart className="w-5 h-5 text-white fill-white/10" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-slate-950 dark:text-white">
              MediScanAI
            </span>
            <span className="text-[10px] block px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400 font-semibold border border-teal-500/20 max-w-max mt-0.5">
              100% LOCAL PRIVACY
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* User profile capsule */}
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60">
            <div className="w-5 h-5 rounded-full bg-teal-600 flex items-center justify-center text-[10px] text-white font-bold uppercase">
              {user.name.charAt(0)}
            </div>
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate max-w-28">
              {user.name}
            </span>
            {user.isGuest && (
              <span className="text-[9px] font-bold tracking-wider text-slate-400 dark:text-slate-500 uppercase px-1">
                Guest
              </span>
            )}
          </div>

          {/* Theme toggler */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all cursor-pointer"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-4.5 h-4.5" /> : <Moon className="w-4.5 h-4.5" />}
          </button>

          {/* Sign out */}
          <button
            onClick={onSignOut}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/20 border border-transparent hover:border-rose-200 dark:hover:border-rose-900/30 transition-all cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </header>

      {/* 2. Main Layout Area */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden max-w-7xl w-full mx-auto p-4 md:p-6 gap-6">
        
        {/* Left Side: Inputs Dashboard Panel */}
        <section className="w-full lg:w-5/12 flex flex-col space-y-5">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl shadow-sm space-y-5">
            <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
              <h2 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">Analyze Health Query</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Combine text symptoms, voice explanations, and medicine package images.</p>
            </div>

            {error && (
              <div className="p-4 text-xs font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/30 rounded-xl space-y-2">
                <p>{error}</p>
                {error.includes("Failed to reach local") && (
                  <button
                    onClick={handleSimulateMock}
                    className="underline text-teal-600 dark:text-teal-400 font-bold block cursor-pointer"
                  >
                    Click here to run in Demo Mock Mode (Simulate local AI response)
                  </button>
                )}
              </div>
            )}

            {/* Input 1: Symptom text */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center space-x-1">
                <FileText className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                <span>Describe Symptoms</span>
              </label>
              <textarea
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                placeholder="Describe what you're experiencing (e.g. Coughing for a week, dry throat, low-grade fever in the evenings)..."
                rows="4"
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 text-sm outline-none focus:border-teal-500 transition-colors resize-none placeholder-slate-400 dark:placeholder-slate-600"
              />
            </div>

            {/* Input 2: Voice recordings */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center space-x-1">
                  <Mic className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                  <span>Voice Recordings</span>
                </label>
                {/* Audio file upload trigger */}
                <label className="text-xs font-bold text-teal-600 dark:text-teal-400 hover:underline cursor-pointer flex items-center space-x-1">
                  <Upload className="w-3 h-3" />
                  <span>Upload Audio</span>
                  <input
                    type="file"
                    accept="audio/*"
                    multiple
                    onChange={handleAudioUpload}
                    className="hidden"
                  />
                </label>
              </div>

              {/* Mic buttons & recording state */}
              <div className="flex items-center space-x-3 p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl">
                {!isRecording ? (
                  <button
                    onClick={startRecording}
                    className="flex items-center space-x-2 bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold py-2.5 px-4 rounded-lg transition-all cursor-pointer shadow-sm"
                  >
                    <Mic className="w-4.5 h-4.5 shrink-0" />
                    <span>Record Live Voice</span>
                  </button>
                ) : (
                  <div className="flex-1 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 rounded-full bg-rose-500 animate-pulse-glow"></div>
                      <span className="text-xs text-rose-500 font-semibold animate-pulse">
                        Recording ({formatDuration(recordingDuration)})
                      </span>
                    </div>
                    <button
                      onClick={stopRecording}
                      className="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold py-1.5 px-3 rounded-md transition-all cursor-pointer"
                    >
                      Stop
                    </button>
                  </div>
                )}
                {!isRecording && (
                  <span className="text-xs text-slate-400 dark:text-slate-500">Record a clip explaining symptoms</span>
                )}
              </div>

              {/* List of Clips */}
              {audioClips.length > 0 && (
                <div className="space-y-2 mt-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  {audioClips.map((clip) => (
                    <div 
                      key={clip.id} 
                      className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
                    >
                      <div className="flex items-center space-x-2 min-w-0">
                        <FileAudio className="w-4.5 h-4.5 text-teal-600 dark:text-teal-400 shrink-0" />
                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate max-w-44">
                          {clip.name}
                        </span>
                        {clip.duration > 0 && (
                          <span className="text-[10px] text-slate-400 dark:text-slate-500">
                            ({formatDuration(clip.duration)})
                          </span>
                        )}
                      </div>
                      
                      <div className="flex items-center space-x-2.5">
                        <button
                          onClick={() => togglePlayClip(clip)}
                          className="p-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-all cursor-pointer"
                          title="Play/Pause"
                        >
                          {playingClipId === clip.id ? <Pause className="w-3.5 h-3.5 text-rose-500" /> : <Play className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          onClick={() => deleteClip(clip.id)}
                          className="p-1 rounded-md hover:bg-rose-50 dark:hover:bg-rose-950/20 text-slate-400 hover:text-rose-500 transition-all cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Input 3: Medicine image upload */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center space-x-1">
                <Image className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                <span>Medicine Package Photo</span>
              </label>

              {!imagePreview ? (
                <div
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  className="border-2 border-dashed border-slate-200 dark:border-slate-800 hover:border-teal-500 dark:hover:border-teal-400 rounded-xl p-8 text-center transition-all cursor-pointer bg-slate-50/50 dark:bg-slate-900/30 flex flex-col items-center justify-center group"
                >
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleImageFile(e.target.files[0])}
                    className="hidden"
                    id="medicine-img-upload"
                  />
                  <label htmlFor="medicine-img-upload" className="cursor-pointer flex flex-col items-center">
                    <Upload className="w-8 h-8 text-slate-400 group-hover:text-teal-500 dark:group-hover:text-teal-400 transition-colors mb-2.5" />
                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Drag & drop photo here</span>
                    <span className="text-xs text-slate-400 dark:text-slate-500 mt-1">or browse files (PNG/JPG up to 10MB)</span>
                  </label>
                </div>
              ) : (
                <div className="relative rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-900 flex justify-center items-center h-48 group">
                  <img 
                    src={imagePreview} 
                    alt="Medicine strip preview" 
                    className="max-h-full object-contain"
                  />
                  
                  {/* Backdrop Overlay */}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center space-x-3">
                    <label 
                      htmlFor="medicine-img-upload" 
                      className="p-2.5 rounded-xl bg-white hover:bg-slate-100 text-slate-800 text-xs font-semibold cursor-pointer shadow-md transition-all"
                    >
                      Replace
                    </label>
                    <button
                      onClick={removeImage}
                      className="p-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md transition-all cursor-pointer"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Submit Trigger */}
            <div className="pt-2">
              <button
                onClick={handleAnalyze}
                disabled={isLoading || (!symptoms.trim() && audioClips.length === 0 && !imageFile)}
                className={`w-full text-white font-bold py-3.5 px-4 rounded-xl transition-all flex items-center justify-center space-x-2 shadow-md ${
                  isLoading || (!symptoms.trim() && audioClips.length === 0 && !imageFile)
                    ? 'bg-slate-300 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed shadow-none'
                    : 'bg-teal-600 hover:bg-teal-500 shadow-teal-600/10 cursor-pointer'
                }`}
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>Analyzing Health Query...</span>
                  </>
                ) : (
                  <span>Run local RAG Analysis</span>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* Right Side: Results Display Panel */}
        <section className="w-full lg:w-7/12 flex flex-col h-full min-h-[500px]">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm flex flex-col h-full min-h-[500px] overflow-hidden">
            
            {/* Standard Dashboard Results Card */}
            {!isLoading && !result && (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 md:p-12 my-auto">
                <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800/80 flex items-center justify-center mb-5 border border-slate-200/50 dark:border-slate-700/30">
                  <Heart className="w-8 h-8 text-teal-600 dark:text-teal-400 fill-teal-600/5" />
                </div>
                <h3 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white mb-2">Awaiting Local Query</h3>
                <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm leading-relaxed mb-6">
                  Fill in symptoms, speak via your mic, or take a picture of your medicine. Click the analyze button to process them locally.
                </p>
                <div className="border border-slate-200/60 dark:border-slate-800 rounded-xl p-4 bg-slate-50/50 dark:bg-slate-950/20 max-w-md text-left text-xs leading-relaxed text-slate-500 dark:text-slate-400 space-y-1.5">
                  <p className="font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1.5 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                    <span>How it works:</span>
                  </p>
                  <p>1. Transcribes speech and cleans text using edit-distance dictionaries.</p>
                  <p>2. Performs PaddleOCR text reading to pull medicine labels from photos.</p>
                  <p>3. Runs vector retrieval searches against diseases and official drug listings.</p>
                  <p>4. Submits aggregated data to your local Mistral model to construct a grounded verdict.</p>
                </div>
              </div>
            )}

            {/* Loading Panel */}
            {isLoading && (
              <div className="flex-1 flex flex-col items-center justify-center p-8 md:p-12 my-auto">
                <div className="relative flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-full border-4 border-teal-500/10 border-t-teal-600 dark:border-t-teal-400 animate-spin"></div>
                  <Heart className="absolute w-6 h-6 text-teal-600 dark:text-teal-400 animate-pulse fill-teal-600/5" />
                </div>
                
                <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white mb-1.5">Processing Query Locally</h3>
                
                {/* Active progress message */}
                <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs text-center leading-relaxed h-10 animate-pulse">
                  {loadingSteps[loadingStep]}
                </p>

                {/* Progress bar visualizer */}
                <div className="w-48 bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 mt-4 overflow-hidden">
                  <div 
                    className="bg-teal-600 dark:bg-teal-400 h-full rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${((loadingStep + 1) / loadingSteps.length) * 100}%` }}
                  ></div>
                </div>
              </div>
            )}

            {/* Displaying Completed Results */}
            {!isLoading && result && (
              <div className="flex-1 flex flex-col overflow-y-auto max-h-[calc(100svh-180px)] p-6 space-y-6">
                
                <div className="border-b border-slate-100 dark:border-slate-800 pb-3 flex justify-between items-center">
                  <h3 className="text-base font-bold tracking-tight text-slate-900 dark:text-white">Analysis Result</h3>
                  <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-1 rounded font-semibold">
                    Local RAG Execution Complete
                  </span>
                </div>

                {/* VERDICT CONTAINER */}
                <div className={`p-5 rounded-2xl border flex items-start space-x-3.5 ${verdictInfo.classes}`}>
                  {verdictInfo.icon}
                  <div className="space-y-1.5">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Verdict Verdict</span>
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${verdictInfo.badge}`}>
                        {verdictInfo.type === 'danger' ? 'Not Suitable' : verdictInfo.type === 'success' ? 'Suitable' : 'Caution'}
                      </span>
                    </div>
                    {/* Render first line from Markdown output as verdict headline */}
                    <p className="text-sm font-semibold leading-relaxed">
                      {cardData?.llm_output.split('\n')[0].replace(/\*\*/g, '')}
                    </p>
                  </div>
                </div>

                {/* DETAILS EXPLANATION */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Explanation</h4>
                  <div className="prose prose-slate dark:prose-invert prose-sm max-w-none text-slate-700 dark:text-slate-300 leading-relaxed">
                    {/* Render everything between first line (verdict) and ### Suggested Alternatives */}
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h3: ({node, ...props}) => <h5 className="text-sm font-bold text-slate-900 dark:text-white mt-4 mb-2" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc pl-4 space-y-1.5 my-2" {...props} />,
                        p: ({node, ...props}) => <p className="mb-3" {...props} />,
                      }}
                    >
                      {getExplanationMarkdown(cardData?.llm_output)}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* SUGGESTED ALTERNATIVES */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Suggested Alternatives</h4>
                  
                  {/* Extract suggested alternatives section markdown */}
                  <div className="prose prose-slate dark:prose-invert prose-sm max-w-none">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h3: () => null, // Hide internal header
                        ul: ({node, ...props}) => <ul className="space-y-3 pl-4 list-disc text-sm text-slate-700 dark:text-slate-300" {...props} />,
                        li: ({node, ...props}) => <li className="marker:text-teal-600 dark:marker:text-teal-400 leading-relaxed" {...props} />,
                        strong: ({node, ...props}) => <strong className="font-bold text-teal-700 dark:text-teal-400" {...props} />,
                      }}
                    >
                      {getAlternativesMarkdown(cardData?.llm_output)}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* RAG EVIDENCE COLLAPSIBLE SECTION */}
                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Grounded Supporting Evidence</h4>
                  
                  <div className="space-y-2">
                    {/* Section 1: Disease match */}
                    {cardData?.retrieved?.diseases && (
                      <div className="border border-slate-200/80 dark:border-slate-800/80 rounded-xl overflow-hidden">
                        <button
                          onClick={() => toggleCollapse('diseases')}
                          className="w-full flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-900/50 text-left text-xs font-semibold cursor-pointer"
                        >
                          <span className="text-slate-700 dark:text-slate-300">Disease Index Matches ({cardData.retrieved.diseases.length})</span>
                          {collapsedSections.diseases ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                        </button>
                        
                        {!collapsedSections.diseases && (
                          <div className="p-3.5 bg-white dark:bg-slate-900/20 border-t border-slate-100 dark:border-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
                            {cardData.retrieved.diseases.map((item, idx) => (
                              <div key={idx} className="py-2.5 first:pt-0 last:pb-0 text-xs">
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className="font-bold text-teal-600 dark:text-teal-400">{item.preview.disease || item.key}</span>
                                  <span className="text-[10px] bg-teal-500/10 text-teal-600 dark:text-teal-400 font-semibold px-2 py-0.5 rounded border border-teal-500/10">
                                    {Math.round(item.score * 100)}% Match
                                  </span>
                                </div>
                                {item.preview.symptoms && (
                                  <p className="text-slate-500 dark:text-slate-400 leading-relaxed">
                                    <strong>Indexed symptoms:</strong> {item.preview.symptoms}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Section 2: Drug matches */}
                    {cardData?.retrieved?.drugs && (
                      <div className="border border-slate-200/80 dark:border-slate-800/80 rounded-xl overflow-hidden">
                        <button
                          onClick={() => toggleCollapse('drugs')}
                          className="w-full flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-900/50 text-left text-xs font-semibold cursor-pointer"
                        >
                          <span className="text-slate-700 dark:text-slate-300">Drug Index Matches ({cardData.retrieved.drugs.length})</span>
                          {collapsedSections.drugs ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                        </button>
                        
                        {!collapsedSections.drugs && (
                          <div className="p-3.5 bg-white dark:bg-slate-900/20 border-t border-slate-100 dark:border-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
                            {cardData.retrieved.drugs.map((item, idx) => (
                              <div key={idx} className="py-2.5 first:pt-0 last:pb-0 text-xs">
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className="font-bold text-teal-600 dark:text-teal-400">
                                    {item.preview.brand_name || item.preview.drug_name || item.key}
                                  </span>
                                  <span className="text-[10px] bg-teal-500/10 text-teal-600 dark:text-teal-400 font-semibold px-2 py-0.5 rounded border border-teal-500/10">
                                    {Math.round(item.score * 100)}% Match
                                  </span>
                                </div>
                                {item.preview.generic_name && (
                                  <p className="text-slate-500 dark:text-slate-400 leading-relaxed mb-1">
                                    <strong>Active Ingredient:</strong> {item.preview.generic_name}
                                  </p>
                                )}
                                {item.preview.indications_and_usage && (
                                  <p className="text-slate-400 dark:text-slate-500 leading-relaxed text-[11px]">
                                    <strong>Indications:</strong> {item.preview.indications_and_usage}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Section 3: OCR Drug Dict matches */}
                    {cardData?.retrieved?.drug_dict && cardData.retrieved.drug_dict.length > 0 && (
                      <div className="border border-slate-200/80 dark:border-slate-800/80 rounded-xl overflow-hidden">
                        <button
                          onClick={() => toggleCollapse('drug_dict')}
                          className="w-full flex items-center justify-between p-3.5 bg-slate-50/50 dark:bg-slate-900/50 text-left text-xs font-semibold cursor-pointer"
                        >
                          <span className="text-slate-700 dark:text-slate-300">OCR Drug Dictionary Matches ({cardData.retrieved.drug_dict.length})</span>
                          {collapsedSections.drug_dict ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                        </button>
                        
                        {!collapsedSections.drug_dict && (
                          <div className="p-3.5 bg-white dark:bg-slate-900/20 border-t border-slate-100 dark:border-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
                            {cardData.retrieved.drug_dict.map((item, idx) => (
                              <div key={idx} className="py-2.5 first:pt-0 last:pb-0 text-xs">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-bold text-teal-600 dark:text-teal-400">{item.preview.brand_name || item.preview.drug_name || item.key}</span>
                                  <span className="text-[10px] bg-teal-500/10 text-teal-600 dark:text-teal-400 font-semibold px-2 py-0.5 rounded border border-teal-500/10">
                                    {Math.round(item.score * 100)}% Match
                                  </span>
                                </div>
                                {item.preview.generic_name && (
                                  <p className="text-slate-500 dark:text-slate-400 leading-relaxed">
                                    <strong>Formula:</strong> {item.preview.generic_name}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* MANDATORY safety warning banner */}
                <div className="p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/30 rounded-2xl flex items-start space-x-3.5 text-xs text-rose-800 dark:text-rose-300 leading-relaxed font-medium">
                  <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 block">⚠️ Medical Disclaimer Warning</span>
                    <p>
                      This analysis is for informational purposes only and is generated based on the data you provided. It is <strong className="font-extrabold underline text-rose-950 dark:text-white">not a substitute for professional medical advice</strong>. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition.
                    </p>
                  </div>
                </div>

              </div>
            )}
            
          </div>
        </section>

      </main>
    </div>
  );
}
