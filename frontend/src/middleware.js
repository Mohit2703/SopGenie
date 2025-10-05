import { NextResponse } from 'next/server';

export function middleware(request) {
  const { pathname } = request.nextUrl;
  
  // Allow all routes to pass through - authentication will be handled client-side
  // Just log for debugging
  console.log('Middleware - Path:', pathname);
  
  // Allow all requests to proceed
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/projects/:path*']
};

