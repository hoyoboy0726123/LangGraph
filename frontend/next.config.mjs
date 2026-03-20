/** @type {import('next').NextConfig} */
const nextConfig = {
  // 代理到 Python FastAPI 後端
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
}

export default nextConfig
