import React, { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import { useHistoryData } from '../providers/HistoryProvider';
import { useAuth } from '../providers/AuthProvider';
import { storage, firebaseConfigured } from '../lib/firebase';
import { getDownloadURL, ref, uploadBytes } from 'firebase/storage';
// CORRECTED: Removed unused FiSend icon
import { FiCheck, FiAlertCircle, FiLoader, FiX, FiPlus, FiArrowUp } from 'react-icons/fi';

type FormState = {
  problemText: string;
  imageFiles: File[];
};

type SubmissionStatus = 'idle' | 'uploading' | 'submitting' | 'success' | 'error';
const MAX_IMAGES = 3;

export const ProblemForm: React.FC = () => {
  const { addItem, loading: historyLoading } = useHistoryData();
  const { user } = useAuth();
  const [form, setForm] = useState<FormState>({ problemText: '', imageFiles: [] });
  const [submissionStatus, setSubmissionStatus] = useState<SubmissionStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const isSubmittable = (form.problemText.trim().length > 0 || form.imageFiles.length > 0) && submissionStatus === 'idle' && !historyLoading;

  // CORRECTED: Memoize previewUrls to prevent re-creation on every render.
  // This makes the dependency for the cleanup useEffect stable and more efficient.
  const previewUrls = useMemo(() => 
    form.imageFiles.map(file => URL.createObjectURL(file)), 
    [form.imageFiles]
  );

  useEffect(() => {
    // This cleanup function will now only run when the component unmounts,
    // preventing memory leaks from the object URLs.
    return () => {
      previewUrls.forEach(url => URL.revokeObjectURL(url));
    };
  }, [previewUrls]);

  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const textarea = e.target;
    setForm(f => ({ ...f, problemText: textarea.value }));
    textarea.style.height = 'auto';
    const maxHeight = 200;
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    if (form.imageFiles.length + files.length > MAX_IMAGES) {
      setStatusMessage(`You can upload a maximum of ${MAX_IMAGES} images.`);
      setSubmissionStatus('error');
      // Add a timeout to clear this specific error message
      setTimeout(() => {
        setSubmissionStatus('idle');
        setStatusMessage('');
      }, 5000);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setForm(f => ({ ...f, imageFiles: [...f.imageFiles, ...files] }));
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRemoveImage = (indexToRemove: number) => {
    // The URL is revoked via the main useEffect cleanup when `previewUrls` updates.
    setForm(f => ({
      ...f,
      imageFiles: f.imageFiles.filter((_, index) => index !== indexToRemove),
    }));
  };

  const handlePreviewClick = (url: string) => {
    setSelectedImage(url);
  };

  const handleClosePreview = () => {
    setSelectedImage(null);
  };

  const uploadImages = async (files: File[]): Promise<string[]> => {
    if (!firebaseConfigured) {
      throw new Error('Firebase Storage not configured');
    }
    const uploadPromises = files.map(file => {
      const fileRef = ref(storage, `problems/${Date.now()}-${file.name}`);
      return uploadBytes(fileRef, file).then(() => getDownloadURL(fileRef));
    });
    return Promise.all(uploadPromises);
  };
  
  const handleSubmission = useCallback(async () => {
    if (!isSubmittable) return;

    if (!user) {
      setStatusMessage('Please login to submit problems');
      setSubmissionStatus('error');
      return;
    }

    setSubmissionStatus('uploading');
    setStatusMessage('Uploading images...');

    try {
      let uploadedImageUrls: string[] = [];
      if (form.imageFiles.length > 0) {
        uploadedImageUrls = await uploadImages(form.imageFiles);
        setStatusMessage('Images uploaded! Submitting problem...');
      }

      setSubmissionStatus('submitting');
      setStatusMessage('Submitting to backend...');
      
      const problemTitle = form.problemText.trim();

      await addItem({
        title: problemTitle.length > 50 ? problemTitle.substring(0, 50) + '...' : problemTitle,
        problemText: problemTitle,
        constraints: undefined,
        testCases: undefined,
        imageUrl: uploadedImageUrls.join(','),
      });

      setSubmissionStatus('success');
      setStatusMessage('Problem submitted successfully! Check history for solution.');
      setForm({ problemText: '', imageFiles: [] });
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
      setTimeout(() => {
        setSubmissionStatus('idle');
        setStatusMessage('');
      }, 3000);

    } catch (error) {
      setSubmissionStatus('error');
      setStatusMessage(error instanceof Error ? error.message : 'Submission failed');
      setTimeout(() => setSubmissionStatus('idle'), 5000);
    }
  }, [user, form, addItem, isSubmittable]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmission();
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmission();
    }
  };

  const getStatusIcon = () => {
    switch (submissionStatus) {
      case 'success':
        return <FiCheck className="text-green-500" />;
      case 'error':
        return <FiAlertCircle className="text-red-500" />;
      case 'uploading':
      case 'submitting':
        return <FiLoader className="animate-spin text-blue-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (submissionStatus) {
      case 'success':
        return 'border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-900 dark:text-green-300';
      case 'error':
        return 'border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900 dark:text-red-300';
      case 'uploading':
      case 'submitting':
        return 'border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-900 dark:text-blue-300';
      default:
        return 'border-neutral-300 bg-neutral-50 text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300';
    }
  };

  return (
    // JSX remains the same
    <div className="flex h-screen flex-col bg-neutral-50 dark:bg-neutral-900">
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm transition-opacity"
          onClick={handleClosePreview}
        >
          <div 
            className="relative max-w-4xl max-h-[90vh] p-4" 
            onClick={(e) => e.stopPropagation()}
          >
            <img src={selectedImage} alt="Full size preview" className="h-auto max-h-[85vh] w-auto rounded-lg shadow-2xl" />
            <button
              type="button"
              onClick={handleClosePreview}
              className="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-neutral-800/80 text-white transition-colors hover:bg-red-600"
              aria-label="Close preview"
            >
              <FiX size={24} />
            </button>
          </div>
        </div>
      )}
      
      <div className="flex-1 flex items-center justify-center p-4">
        {form.problemText.trim() === '' && form.imageFiles.length === 0 && (
          <h1 className="text-2xl font-semibold bg-gradient-to-r from-purple-500 to-blue-500 dark:from-purple-400 dark:to-blue-400 bg-clip-text text-transparent [filter:drop-shadow(0_2px_3px_rgba(168,85,247,0.4))]">
            Hello {user?.displayName || 'User'}, how can I help you today?
          </h1>
        )}
      </div>

      <form
        onSubmit={onSubmit}
        className="sticky bottom-0 left-0 right-0 w-full bg-neutral-50/80 p-4 backdrop-blur-sm dark:bg-neutral-900/80"
      >
        <div className="mx-auto max-w-4xl">
          {statusMessage && (
            <div className={`p-3 mb-3 rounded-xl border shadow-sm flex items-center gap-2 text-sm ${getStatusColor()}`}>
              {getStatusIcon()}
              <span className="font-medium">{statusMessage}</span>
            </div>
          )}

          {previewUrls.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-3">
              {previewUrls.map((url, index) => (
                <div key={index} className="relative h-20 w-20">
                  <button
                    type="button"
                    onClick={() => handlePreviewClick(url)}
                    className="block h-full w-full rounded-lg overflow-hidden focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900"
                  >
                    <img
                      src={url} alt={`Preview ${index + 1}`}
                      className="h-full w-full object-cover"
                    />
                  </button>
                  <button
                    type="button" onClick={() => handleRemoveImage(index)}
                    className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-neutral-800 text-white hover:bg-red-600 transition-colors"
                    aria-label="Remove image"
                  >
                    <FiX size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="relative flex w-full items-end gap-2 rounded-2xl border border-neutral-300 bg-white p-2 shadow-md transition-all focus-within:border-purple-500 focus-within:shadow-lg focus-within:shadow-purple-500/20 dark:border-neutral-700 dark:bg-neutral-800 dark:focus-within:border-purple-500">
            <label className="flex-shrink-0 cursor-pointer rounded-full p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handleFileChange}
                disabled={form.imageFiles.length >= MAX_IMAGES}
              />
              <FiPlus className="h-6 w-6 text-neutral-600 dark:text-neutral-400" />
            </label>

            <textarea
              ref={textareaRef}
              name="problemText"
              value={form.problemText}
              onChange={handleTextChange}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Describe your problem..."
              className="w-full flex-1 resize-none self-center border-none bg-transparent py-1.5 align-middle text-base placeholder-neutral-500 focus:outline-none focus:ring-0 dark:text-white dark:placeholder-neutral-400"
              style={{ maxHeight: '200px' }}
            />

            {isSubmittable && (
              <button
                type="submit"
                disabled={!isSubmittable}
                className="flex-shrink-0 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 p-2 text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                aria-label="Submit problem"
              >
                <FiArrowUp className="h-6 w-6" />
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};