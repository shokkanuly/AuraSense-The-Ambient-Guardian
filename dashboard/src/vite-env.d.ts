/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HUB_URL?: string;
  readonly VITE_PAIRING_CODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
