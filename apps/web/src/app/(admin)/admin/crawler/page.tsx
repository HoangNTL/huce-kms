"use client"

import * as React from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  DirectCrawlTab,
  DiscoveryTab,
  QueueTab,
  SessionsTab,
  crawlerService,
} from "@/features/crawler"
import { categoryService, type CategoryItem } from "@/features/categories"

export default function AdminCrawlerPage() {
  const [activeTab, setActiveTab] = React.useState("direct")
  const [categories, setCategories] = React.useState<CategoryItem[]>([])
  const [queueCount, setQueueCount] = React.useState<number>(0)

  const refreshQueueCount = React.useCallback(() => {
    crawlerService
      .getQueue()
      .then((q) => setQueueCount(q?.approved_total ?? q?.approved_urls?.length ?? 0))
      .catch(() => {})
  }, [])

  React.useEffect(() => {
    categoryService
      .getCategories()
      .then((data) => setCategories(data || []))
      .catch(() => {
        // Fallback silently if category service is unavailable
      })
  }, [])

  React.useEffect(() => {
    refreshQueueCount()
  }, [refreshQueueCount, activeTab])

  return (
    <div className="space-y-6">
      {/* Page Title: Clean & Focused, consistent with other admin management pages */}
      <div>
        <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
          Thu thập dữ liệu
        </h1>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex flex-col w-full gap-3"
      >
        <TabsList className="h-9 w-fit bg-surface border border-border p-1">
          <TabsTrigger
            value="direct"
            className="text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold"
          >
            Theo liên kết
          </TabsTrigger>
          <TabsTrigger
            value="discovery"
            className="text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold"
          >
            Khám phá
          </TabsTrigger>
          <TabsTrigger
            value="queue"
            className="text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold flex items-center gap-1.5"
          >
            <span>Hàng đợi</span>
            {queueCount > 0 && (
              <span className="rounded-full bg-brand-primary/10 text-brand-primary px-1.5 py-0.5 text-2xs font-semibold leading-none">
                {queueCount}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="sessions"
            className="text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold"
          >
            Lịch sử
          </TabsTrigger>
        </TabsList>

        <TabsContent value="direct">
          <DirectCrawlTab categories={categories} />
        </TabsContent>

        <TabsContent value="discovery">
          <DiscoveryTab
            onApproved={() => {
              setActiveTab("queue")
              refreshQueueCount()
            }}
          />
        </TabsContent>

        <TabsContent value="queue">
          <QueueTab
            categories={categories}
            onCompleted={() => {
              setActiveTab("sessions")
              refreshQueueCount()
            }}
          />
        </TabsContent>

        <TabsContent value="sessions">
          <SessionsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
