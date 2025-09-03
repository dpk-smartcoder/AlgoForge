export async function uploadImageToCloudinary(file: File): Promise<string> {
  const cloudName = process.env.REACT_APP_CLOUDINARY_CLOUD_NAME;
  const uploadPreset = process.env.REACT_APP_CLOUDINARY_UPLOAD_PRESET;
  if (!cloudName || !uploadPreset) {
    throw new Error('Cloudinary env not configured');
  }

  const form = new FormData();
  form.append('file', file);
  form.append('upload_preset', uploadPreset);

  const res = await fetch(`https://api.cloudinary.com/v1_1/${cloudName}/image/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error('Cloudinary upload failed');
  const data = await res.json();
  return data.secure_url as string;
}

export function cloudinaryConfigured(): boolean {
  return Boolean(process.env.REACT_APP_CLOUDINARY_CLOUD_NAME && process.env.REACT_APP_CLOUDINARY_UPLOAD_PRESET);
}


