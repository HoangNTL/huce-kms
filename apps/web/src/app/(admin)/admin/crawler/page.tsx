"use client"

import * as React from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  DirectCrawlTab,
  DiscoveryTab,
  QueueTab,
  SessionsTab,
} from "@/features/crawler"
import { categoryService, type CategoryItem } from "@/features/categories"

export default function AdminCrawlerPage() {
  const [activeTab, setActiveTab] = React.useState("direct")
  const [categories, setCategories] = React.useState<CategoryItem[]>([])

  React.useEffect(() => {
    categoryService
      .getCategories()
      .then((data) => setCategories(data || []))
      .catch(() => {
        // Fallback silently if category service is unavailable
      })
  }, [])

  return (
    <div className="space-y-6">
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
            className="text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold"
          >
            Hàng đợi
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
          <DiscoveryTab onApproved={() => setActiveTab("queue")} />
        </TabsContent>

        <TabsContent value="queue">
          <QueueTab
            categories={categories}
            onCompleted={() => setActiveTab("sessions")}
          />
        </TabsContent>

        <TabsContent value="sessions">
          <SessionsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
