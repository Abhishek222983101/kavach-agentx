/** Resize a photo in the browser before upload (max 1280 px, JPEG): faster to send, same evidence. */
export async function toDataUrl(file: Blob, max = 1280): Promise<string> {
  const bmp = await createImageBitmap(file);
  const k = Math.min(1, max / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
  c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.85);
}

export async function sampleDataUrl(id: string): Promise<string> {
  const r = await fetch(`/samples/${id}.jpg`);
  return toDataUrl(await r.blob());
}
