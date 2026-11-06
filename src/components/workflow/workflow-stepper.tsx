"use client"

import { CheckCircle2Icon, CircleIcon } from "lucide-react"

interface Step {
  id: string
  title: string
  description: string
}

interface WorkflowStepperProps {
  currentStep: number
  steps: Step[]
}

export function WorkflowStepper({ currentStep, steps }: WorkflowStepperProps) {
  return (
    <div className="flex items-center justify-between">
      {steps.map((step, index) => {
        const isCompleted = index < currentStep
        const isCurrent = index === currentStep
        return (
          <div key={step.id} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1">
              <div className={`flex size-8 items-center justify-center rounded-full ${
                isCompleted ? "bg-primary text-primary-foreground" :
                isCurrent ? "border-2 border-primary text-primary" :
                "border-2 border-border text-muted-foreground"
              }`}>
                {isCompleted ? <CheckCircle2Icon className="size-5" /> : <span>{index + 1}</span>}
              </div>
              <div className="text-center">
                <p className={`text-xs font-medium ${isCurrent ? "text-foreground" : "text-muted-foreground"}`}>
                  {step.title}
                </p>
                <p className="text-xs text-muted-foreground">{step.description}</p>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div className={`mx-2 h-0.5 flex-1 ${index < currentStep ? "bg-primary" : "bg-border"}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
