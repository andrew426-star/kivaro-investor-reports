import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { WorkflowIcon } from 'lucide-react'

export default function Home() {
  return (
    <div className='mx-auto flex w-full max-w-4xl flex-1 flex-col items-center justify-center gap-6 px-4 py-12 text-center'>
      <div className='flex flex-col gap-2'>
        <h1 className='font-heading text-4xl text-gradient-green sm:text-5xl'>Kivaro Investor Reports</h1>
        <p className='text-lg text-muted-foreground'>Drop-and-generate workflow for detailed investor reports</p>
      </div>
      <Link href='/workflow'>
        <Button size='lg'><WorkflowIcon className='size-5' />Start New Report Workflow</Button>
      </Link>
    </div>
  )
}
