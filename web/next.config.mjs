import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  webpack(config) {
    config.resolve.alias["@contracts"] = path.resolve(
      __dirname,
      "../packages/contracts/ts/index.ts",
    );
    return config;
  },
};

export default nextConfig;
