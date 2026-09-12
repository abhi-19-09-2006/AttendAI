'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect root to dashboard (which handles auth redirection if needed)
    router.replace('/dashboard')
  }, [router])

  return null
}
