const MAX_PROFILE_IMAGE_SIZE = 512;
const PROFILE_IMAGE_QUALITY = 0.86;

export async function fileToProfileImage(file: File): Promise<string> {
  if (!file.type.startsWith("image/")) {
    throw new Error("Lütfen bir görsel dosyası seçin.");
  }

  const image = await loadImage(file);
  const scale = Math.min(1, MAX_PROFILE_IMAGE_SIZE / Math.max(image.width, image.height));
  const width = Math.max(1, Math.round(image.width * scale));
  const height = Math.max(1, Math.round(image.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Profil resmi işlenemedi.");
  }

  context.drawImage(image, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", PROFILE_IMAGE_QUALITY);
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Profil resmi okunamadı."));
    };
    image.src = objectUrl;
  });
}
