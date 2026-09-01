import React, { useState, useRef, useCallback } from 'react';
import {
  Camera,
  AlertCircle,
  Sparkles,
  Play,
  CheckCircle2,
  Layers,
  X,
  Plus,
  Tag,
  ChevronDown,
  SwitchCamera,
  ScanLine,
} from 'lucide-react';
import { inspectionService } from '../services/inspectionService';
import { demoService } from '../services/demoService';
import { DemoSample, InspectionResponse } from '../types/inspection';
import { PipelineStepperModal } from '../components/inspection/PipelineStepperModal';
import { StatusBadge } from '../components/common/StatusBadge';

interface NewInspectionPageProps {
  onInspectionComplete: (result: InspectionResponse) => void;
}

interface PhotoSlot {
  id: string;
  file: File;
  previewUrl: string;
  panelTag: string;
  meta: { width: number; height: number; sizeMb: number } | null;
}

const PANEL_TAGS = [
  'Front', 'Back', 'Side', 'Neck', 'Top', 'Bottom',
  'Batch Seal', 'Barcode', 'Nutritional', 'General',
];

const TAG_COLORS: Record<string, string> = {
  Front:        'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  Back:         'bg-sky-500/20 text-sky-300 border-sky-500/40',
  Side:         'bg-violet-500/20 text-violet-300 border-violet-500/40',
  Neck:         'bg-purple-500/20 text-purple-300 border-purple-500/40',
  Top:          'bg-amber-500/20 text-amber-300 border-amber-500/40',
  Bottom:       'bg-orange-500/20 text-orange-300 border-orange-500/40',
  'Batch Seal': 'bg-rose-500/20 text-rose-300 border-rose-500/40',
  Barcode:      'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
  Nutritional:  'bg-teal-500/20 text-teal-300 border-teal-500/40',
  General:      'bg-slate-500/20 text-slate-300 border-slate-500/40',
};

function getAutoTag(index: number): string {
  const auto = ['Front', 'Back', 'Side', 'Neck', 'Top', 'Bottom'];
  return auto[index] ?? `Photo ${index + 1}`;
}

let _idCounter = 0;
function genId() { return `slot_${++_idCounter}_${Date.now()}`; }

export const NewInspectionPage: React.FC<NewInspectionPageProps> = ({ onInspectionComplete }) => {
  const [photos, setPhotos] = useState<PhotoSlot[]>([]);
  const [activeTab, setActiveTab] = useState<'upload' | 'demo'>('upload');
  const [productCategory, setProductCategory] = useState<string>('packaged_commodity');
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraFacingMode, setCameraFacingMode] = useState<'environment' | 'user'>('environment');
  const [isCapturing, setIsCapturing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStage, setCurrentStage] = useState(1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [demoSamples, setDemoSamples] = useState<DemoSample[]>([]);
  const [selectedDemoKey, setSelectedDemoKey] = useState<string>('compliant_shampoo');
  const [isDragOver, setIsDragOver] = useState(false);
  const [openTagMenu, setOpenTagMenu] = useState<string | null>(null);

  const batchFileInputRef = useRef<HTMLInputElement | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  React.useEffect(() => {
    demoService.getDemoSamples().then(setDemoSamples).catch(console.error);
  }, []);

  React.useEffect(() => {
    const handler = () => setOpenTagMenu(null);
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const addFilesToSlots = useCallback((files: File[]) => {
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    const valid = files.filter((f) => validTypes.includes(f.type));
    if (!valid.length) return;
    valid.forEach((file) => {
      const id = genId();
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        setPhotos((prev) => {
          const autoTag = getAutoTag(prev.length);
          return [
            ...prev,
            {
              id,
              file,
              previewUrl: url,
              panelTag: autoTag,
              meta: {
                width: img.width,
                height: img.height,
                sizeMb: parseFloat((file.size / (1024 * 1024)).toFixed(2)),
              },
            },
          ];
        });
      };
      img.src = url;
    });
    setErrorMsg(null);
  }, []);

  const removePhoto = (id: string) => {
    setPhotos((prev) => {
      const slot = prev.find((p) => p.id === id);
      if (slot) URL.revokeObjectURL(slot.previewUrl);
      return prev.filter((p) => p.id !== id);
    });
  };

  const setTag = (id: string, tag: string) => {
    setPhotos((prev) => prev.map((p) => (p.id === id ? { ...p, panelTag: tag } : p)));
    setOpenTagMenu(null);
  };

  const stopCamera = useCallback(() => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setIsCameraActive(false);
    setIsCapturing(false);
  }, []);

  React.useEffect(() => () => stopCamera(), [stopCamera]);

  React.useEffect(() => {
    if (isCameraActive && videoRef.current && mediaStreamRef.current) {
      videoRef.current.srcObject = mediaStreamRef.current;
    }
  }, [isCameraActive]);

  const startCamera = async (facingMode = cameraFacingMode) => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMsg('This browser does not support camera access. Please upload a photo instead.');
      return;
    }

    try {
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      mediaStreamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraFacingMode(facingMode);
      setErrorMsg(null);
      setIsCameraActive(true);
    } catch (error) {
      const message = error instanceof DOMException && error.name === 'NotAllowedError'
        ? 'Camera permission was denied. Allow access in your browser settings and try again.'
        : 'Camera access is unavailable. Check that no other app is using the camera.';
      setErrorMsg(message);
    }
  };

  const switchCamera = () => {
    startCamera(cameraFacingMode === 'environment' ? 'user' : 'environment');
  };

  const capturePhoto = () => {
    if (!videoRef.current || !videoRef.current.videoWidth || !videoRef.current.videoHeight) {
      setErrorMsg('The camera is still starting. Please wait a moment and try again.');
      return;
    }
    setIsCapturing(true);
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(videoRef.current, 0, 0);
      canvas.toBlob((blob) => {
        if (blob) {
          addFilesToSlots([new File([blob], `product-scan-${Date.now()}.jpg`, { type: 'image/jpeg' })]);
          stopCamera();
        } else {
          setIsCapturing(false);
          setErrorMsg('Could not capture the image. Please try again.');
        }
      }, 'image/jpeg', 0.92);
    }
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragOver(true); };
  const handleDragLeave = () => setIsDragOver(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    addFilesToSlots(Array.from(e.dataTransfer.files));
  };

  const runAnalysis = async () => {
    if (activeTab === 'demo') { runDemoAnalysis(); return; }
    if (photos.length === 0) { setErrorMsg('Please upload at least one photo.'); return; }
    setIsAnalyzing(true);
    setErrorMsg(null);
    setCurrentStage(1);
    const interval = setInterval(() => setCurrentStage((prev) => (prev < 7 ? prev + 1 : prev)), 450);
    try {
      const files = photos.map((p) => p.file);
      const panelTypes = photos.map((p) => p.panelTag.toLowerCase().replace(/\s+/g, '_'));
      const result = await inspectionService.uploadAndAnalyze(files, productCategory, panelTypes);
      setCurrentStage(8);
      setTimeout(() => {
        clearInterval(interval);
        setIsAnalyzing(false);
        onInspectionComplete(result);
      }, 500);
    } catch (err: any) {
      clearInterval(interval);
      setIsAnalyzing(false);
      setErrorMsg(err.message ?? 'Pipeline processing failed.');
    }
  };

  const runDemoAnalysis = async () => {
    setIsAnalyzing(true);
    setErrorMsg(null);
    setCurrentStage(1);
    const interval = setInterval(() => setCurrentStage((prev) => (prev < 7 ? prev + 1 : prev)), 400);
    try {
      const result = await demoService.runDemoInspection(selectedDemoKey);
      setCurrentStage(8);
      setTimeout(() => {
        clearInterval(interval);
        setIsAnalyzing(false);
        onInspectionComplete(result);
      }, 400);
    } catch (err: any) {
      clearInterval(interval);
      setIsAnalyzing(false);
      setErrorMsg(err.message ?? 'Demo failed.');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fadeIn">
      <div className="space-y-1.5">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          New Legal Metrology Inspection
        </h1>
        <p className="text-sm text-slate-400">
          Upload <strong className="text-slate-300">any number of photos</strong> from any part of the
          package. The AI fuses all panels to extract every mandatory declaration.
        </p>
      </div>

      <div className="flex border-b border-slate-800 space-x-4">
        <button
          onClick={() => { setActiveTab('upload'); setErrorMsg(null); }}
          className={`pb-3 text-sm font-semibold border-b-2 transition-all ${activeTab === 'upload' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
        >
          Photo Upload / Camera
        </button>
        <button
          onClick={() => { setActiveTab('demo'); setErrorMsg(null); }}
          className={`pb-3 text-sm font-semibold border-b-2 flex items-center space-x-1.5 transition-all ${activeTab === 'demo' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
        >
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>Curated Demo Scenarios</span>
        </button>
      </div>

      {activeTab === 'upload' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-5">
            <div className="flex items-start space-x-3 p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-slate-300 leading-relaxed">
              <Layers className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <span>
                <strong className="text-indigo-300">Tip: </strong>
                Upload photos of any package surface — Front, Back, Side, Neck, Batch Seal, Barcode, etc.
                Tag each photo and the AI applies the right field-affinity weights per surface.
              </span>
            </div>

            {isCameraActive && (
              <div className="rounded-3xl overflow-hidden bg-slate-950 border border-slate-700 shadow-2xl shadow-black/30">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                  <div className="flex items-center gap-2 text-left">
                    <ScanLine className="w-4 h-4 text-emerald-400" />
                    <div>
                      <p className="text-sm font-semibold text-slate-100">Product scanner</p>
                      <p className="text-[11px] text-slate-400">Align the label inside the frame</p>
                    </div>
                  </div>
                  <button onClick={switchCamera} className="p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors" title="Switch camera" aria-label="Switch camera">
                    <SwitchCamera className="w-4 h-4" />
                  </button>
                </div>
                <div className="relative bg-black aspect-[4/3] max-h-[28rem]">
                  <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                  <div className="absolute inset-[12%] rounded-2xl border-2 border-white/80 shadow-[0_0_0_999px_rgba(0,0,0,0.38)] pointer-events-none">
                    <span className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap text-[11px] text-white/90">Keep the declaration text clear</span>
                  </div>
                </div>
                <div className="flex justify-center gap-3 p-4">
                  <button disabled={isCapturing} onClick={capturePhoto} className="px-6 py-2.5 rounded-xl bg-emerald-500 text-white font-semibold text-sm hover:bg-emerald-600 disabled:opacity-60 transition-colors">
                    {isCapturing ? 'Capturing…' : 'Capture product'}
                  </button>
                  <button onClick={stopCamera} className="px-4 py-2.5 rounded-xl bg-slate-800 text-slate-300 font-semibold text-sm hover:bg-slate-700 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {!isCameraActive && (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => batchFileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-200 py-8 px-6 ${isDragOver ? 'border-emerald-500 bg-emerald-500/10 scale-[1.01]' : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800/30 bg-slate-900/40'}`}
              >
                <div className="p-3 rounded-2xl bg-slate-800 border border-slate-700">
                  <Plus className="w-7 h-7 text-emerald-400" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-slate-200">
                    {isDragOver ? 'Drop photos here' : 'Click to add photos or drag & drop'}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">PNG, JPG, WEBP — any number of photos</p>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); startCamera(); }}
                  className="inline-flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 transition-colors"
                >
                  <Camera className="w-3.5 h-3.5" />
                  <span>Use Camera</span>
                </button>
                <input
                  ref={batchFileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files) addFilesToSlots(Array.from(e.target.files));
                    e.target.value = '';
                  }}
                />
              </div>
            )}

            {photos.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    {photos.length} Photo{photos.length !== 1 ? 's' : ''} Ready
                  </span>
                  <button
                    type="button"
                    onClick={() => batchFileInputRef.current?.click()}
                    className="inline-flex items-center space-x-1 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-emerald-400 hover:bg-slate-700 transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    <span>Add More</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {photos.map((photo, idx) => {
                    const tagColor = TAG_COLORS[photo.panelTag] ?? TAG_COLORS['General'];
                    const isMenuOpen = openTagMenu === photo.id;
                    return (
                      <div key={photo.id} className="relative group flex flex-col space-y-1.5">
                        <div className="relative rounded-xl overflow-hidden aspect-[3/4] bg-slate-950 border border-slate-800 group-hover:border-slate-600 transition-all shadow-lg">
                          <img src={photo.previewUrl} alt={`Photo ${idx + 1}`} className="w-full h-full object-cover" />
                          {photo.meta && (
                            <div className="absolute bottom-0 inset-x-0 p-1.5 bg-gradient-to-t from-black/75 to-transparent">
                              <p className="text-[9px] font-mono text-slate-300 text-center">
                                {photo.meta.width} x {photo.meta.height} &middot; {photo.meta.sizeMb} MB
                              </p>
                            </div>
                          )}
                          {photo.meta && (
                            <div className={`absolute top-1.5 left-1.5 text-[8px] font-bold px-1 py-0.5 rounded uppercase tracking-wide ${photo.meta.width >= 400 && photo.meta.height >= 400 ? 'bg-emerald-500/80 text-white' : 'bg-amber-500/80 text-white'}`}>
                              {photo.meta.width >= 400 && photo.meta.height >= 400 ? 'HD' : 'Low'}
                            </div>
                          )}
                          <button
                            onClick={() => removePhoto(photo.id)}
                            className="absolute top-1.5 right-1.5 p-1 rounded-lg bg-rose-600/80 hover:bg-rose-600 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Remove"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                        <div className="relative">
                          <button
                            type="button"
                            onMouseDown={(e) => { e.stopPropagation(); setOpenTagMenu(isMenuOpen ? null : photo.id); }}
                            className={`w-full flex items-center justify-between px-2 py-1 rounded-lg border text-[10px] font-bold uppercase tracking-wide transition-all ${tagColor}`}
                          >
                            <span className="flex items-center space-x-1">
                              <Tag className="w-2.5 h-2.5" />
                              <span>{photo.panelTag}</span>
                            </span>
                            <ChevronDown className="w-2.5 h-2.5" />
                          </button>
                          {isMenuOpen && (
                            <div
                              onMouseDown={(e) => e.stopPropagation()}
                              className="absolute z-50 left-0 top-full mt-1 w-44 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl py-1 overflow-hidden"
                            >
                              {PANEL_TAGS.map((tag) => (
                                <button
                                  key={tag}
                                  type="button"
                                  onClick={() => setTag(photo.id, tag)}
                                  className={`w-full text-left px-3 py-1.5 text-[11px] font-semibold hover:bg-slate-800 transition-colors ${photo.panelTag === tag ? 'text-emerald-400' : 'text-slate-300'}`}
                                >
                                  {tag}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {!isCameraActive && photos.length > 0 && (
              <div className="flex items-center space-x-2 text-xs text-slate-400 pl-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  <strong className="text-emerald-400">{photos.length}</strong> photo{photos.length !== 1 ? 's' : ''} ready &mdash; all panels will be fused for maximum compliance coverage.
                </span>
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl space-y-3">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">Product Category</label>
              <p className="text-xs text-slate-400">Determines the Legal Metrology compliance rules to load.</p>
              <select
                value={productCategory}
                onChange={(e) => setProductCategory(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs font-medium focus:outline-none focus:border-emerald-500 transition-colors"
              >
                <option value="packaged_commodity">General Packaged Commodities</option>
                <option value="food_and_beverages">Food and Beverages (FSSAI + LM)</option>
                <option value="cosmetics_and_toiletries">Cosmetics and Toiletries</option>
                <option value="electronics_and_appliances">Electronics and Electrical Appliances</option>
                <option value="pharmaceuticals">Pharmaceuticals and Healthcare</option>
              </select>
            </div>

            <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Statutory Audit Checks</h4>
              <ul className="space-y-2 text-xs text-slate-400">
                {[
                  'Image sharpness and glare assessment',
                  'MRP (Inclusive of all taxes) verification',
                  'Standard SI Net Quantity parsing',
                  'Mfg date and Expiry date extraction',
                  'Manufacturer and Consumer Care audit',
                  'Multi-panel cross-field fusion',
                ].map((c) => (
                  <li key={c} className="flex items-center space-x-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={runAnalysis}
              disabled={photos.length === 0 || isAnalyzing}
              className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm flex items-center justify-center space-x-2 shadow-xl transition-all duration-200 ${photos.length > 0 && !isAnalyzing ? 'bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white shadow-emerald-600/30 hover:scale-[1.02] active:scale-[0.98]' : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'}`}
            >
              <Play className="w-4 h-4 fill-current" />
              <span>
                {photos.length > 1
                  ? `Run Multi-Panel Analysis (${photos.length} photos)`
                  : photos.length === 1
                  ? 'Execute Compliance Pipeline'
                  : 'Upload Photos First'}
              </span>
            </button>

            {errorMsg && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span className="text-xs text-rose-300">{errorMsg}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'demo' && (
        <div className="space-y-6">
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-slate-300 leading-relaxed">
            <span className="font-semibold text-emerald-300">Curated Demo Mode: </span>
            Select a verified packaged commodity label scenario to observe how the AI pipeline handles ideal compliance, missing declarations, blur, and multipacks.
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {demoSamples.map((sample) => {
              const isSelected = selectedDemoKey === sample.key;
              return (
                <div
                  key={sample.key}
                  onClick={() => setSelectedDemoKey(sample.key)}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all duration-200 space-y-3 ${isSelected ? 'bg-emerald-500/10 border-emerald-500/50 shadow-lg shadow-emerald-500/10 scale-[1.02]' : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'}`}
                >
                  <div className="flex items-start justify-between">
                    <h4 className="text-sm font-bold text-slate-100">{sample.title}</h4>
                    <StatusBadge status={sample.expected_verdict} size="sm" />
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{sample.description}</p>
                  <div className="text-[11px] text-slate-500 font-mono pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <span>Category: {sample.category}</span>
                    <span className="text-emerald-400 font-semibold">{isSelected ? 'Selected' : 'Click to Select'}</span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-end pt-4">
            <button
              onClick={runAnalysis}
              disabled={isAnalyzing}
              className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-sm shadow-lg shadow-emerald-600/30 hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              Run Selected Demo Scenario
            </button>
          </div>
        </div>
      )}

      {isAnalyzing && (
        <PipelineStepperModal
          currentStage={currentStage}
          isComplete={currentStage === 8}
          error={errorMsg}
        />
      )}
    </div>
  );
};
