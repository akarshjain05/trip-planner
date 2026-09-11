import { useState, useEffect } from "react";
import type { Activity, ItineraryDay } from "../types";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { reorderActivities } from "../services/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

const ACTIVITY_ICON: Record<Activity["activity_type"], string> = {
  flight: "\u2708",
  transfer: "\uD83D\uDE95",
  meal: "\uD83C\uDF7D",
  attraction: "\uD83D\uDCCD",
  hotel_checkin: "\uD83D\uDECC",
  hotel_checkout: "\uD83C\uDFE8",
  free_time: "\u2600",
  other: "\u2022",
};

function formatCurrency(amount: number | null, currency: string): string {
  if (amount === null || amount === 0) return "";
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

function SortableActivityItem({ activity, currency }: { activity: Activity; currency: string }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: activity.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : 0,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-start gap-3 py-2.5 bg-paper relative group"
    >
      <div 
        {...attributes} 
        {...listeners}
        className="cursor-grab opacity-0 group-hover:opacity-50 hover:!opacity-100 absolute -left-6 top-1/2 -translate-y-1/2 p-1"
        aria-label="Drag to reorder"
      >
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="9" cy="12" r="1"></circle>
          <circle cx="9" cy="5" r="1"></circle>
          <circle cx="9" cy="19" r="1"></circle>
          <circle cx="15" cy="12" r="1"></circle>
          <circle cx="15" cy="5" r="1"></circle>
          <circle cx="15" cy="19" r="1"></circle>
        </svg>
      </div>
      <span className="font-mono text-xs text-paper-ink/50 w-12 shrink-0 pt-0.5">
        {activity.time ?? ""}
      </span>
      <span className="shrink-0" aria-hidden>{ACTIVITY_ICON[activity.activity_type]}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-paper-ink font-medium">{activity.title}</p>
        {activity.description && (
          <p className="text-xs text-paper-ink/60 mt-0.5 leading-relaxed">{activity.description}</p>
        )}
      </div>
      {activity.estimated_cost != null && activity.estimated_cost > 0 && (
        <span className="font-mono text-xs text-paper-ink/70 shrink-0">
          {formatCurrency(activity.estimated_cost, currency)}
        </span>
      )}
    </div>
  );
}

export function ItineraryDayCard({ day, currency, tripId }: { day: ItineraryDay; currency: string, tripId: string }) {
  const [items, setItems] = useState(day.activities);
  const queryClient = useQueryClient();

  useEffect(() => {
    setItems(day.activities);
  }, [day.activities]);

  const reorderMutation = useMutation({
    mutationFn: (newItems: Activity[]) => {
      const activityIds = newItems.map(item => item.id);
      return reorderActivities(tripId, day.id, activityIds);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["itinerary", tripId] });
    },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
        activationConstraint: {
            distance: 5,
        },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setItems((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);

        const newItems = arrayMove(items, oldIndex, newIndex);
        reorderMutation.mutate(newItems);
        return newItems;
      });
    }
  }

  return (
    <div className="ticket-card px-8 py-6">
      <div className="flex items-baseline justify-between mb-1 flex-wrap gap-x-4 gap-y-1">
        <h3 className="font-display text-xl text-paper-ink">{day.title ?? `Day ${day.day_number}`}</h3>
        {day.weather_summary && (
          <span className="font-mono text-xs text-paper-ink/60">{day.weather_summary}</span>
        )}
      </div>
      {day.date && (
        <p className="font-mono text-[11px] text-paper-ink/50 mb-4 tracking-wide">{day.date}</p>
      )}

      <div className="flex flex-col divide-y divide-paper-ink/10 mt-4 pl-4">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={items.map(item => item.id)}
            strategy={verticalListSortingStrategy}
          >
            {items.map((activity) => (
              <SortableActivityItem key={activity.id} activity={activity} currency={currency} />
            ))}
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
}
