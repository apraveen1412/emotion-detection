const bufferToBase64 = (buffer) => {
  const bytes = new Uint8Array(buffer);
  return window.btoa(String.fromCharCode(...bytes));
};

const base64ToBuffer = (base64) => {
  const binaryString = window.atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
};

export const getOrCreateKey = async () => {
  const storedKey = localStorage.getItem("e2ee_key");
  if (storedKey) {
    const keyBuffer = base64ToBuffer(storedKey);
    return await window.crypto.subtle.importKey(
      "raw", keyBuffer, { name: "AES-GCM" }, true, ["encrypt", "decrypt"]
    );
  }
  const newKey = await window.crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]
  );
  const exportedKey = await window.crypto.subtle.exportKey("raw", newKey);
  localStorage.setItem("e2ee_key", bufferToBase64(exportedKey));
  return newKey;
};

export const encryptText = async (text) => {
  if (!text) return "";
  const key = await getOrCreateKey();
  const encoder = new TextEncoder();
  const iv = window.crypto.getRandomValues(new Uint8Array(12));
  const ciphertextBuffer = await window.crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv }, key, encoder.encode(text)
  );
  const combined = new Uint8Array(iv.length + ciphertextBuffer.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertextBuffer), iv.length);
  return bufferToBase64(combined.buffer);
};