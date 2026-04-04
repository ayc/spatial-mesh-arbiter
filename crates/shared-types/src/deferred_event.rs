use core::fmt;

use crate::{DeferredTargetStageId, EntityId};

/// Current deferred event classes in the active runtime profile.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum DeferredEventClass {
    DeferredSpatialEvent,
    DeferredCombatEvent,
}

/// Errors returned when constructing or validating deferred events.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DeferredEventError {
    InvalidClassTargetPair {
        event_class: DeferredEventClass,
        target_stage: DeferredTargetStageId,
    },
}

impl fmt::Display for DeferredEventError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DeferredEventError::InvalidClassTargetPair {
                event_class,
                target_stage,
            } => write!(
                f,
                "invalid deferred event pair: class={event_class:?}, target_stage={target_stage:?}"
            ),
        }
    }
}

/// Deferred work admitted by the scheduler on a later authoritative tick.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DeferredEvent<TPayload, TEntityId = EntityId> {
    pub target_stage: DeferredTargetStageId,
    pub event_class: DeferredEventClass,
    pub source_entity_id: TEntityId,
    pub ready_tick: u64,
    pub sort_key: u64,
    pub payload: TPayload,
}

impl<TPayload, TEntityId> DeferredEvent<TPayload, TEntityId> {
    pub const fn is_current_profile_pair_valid(
        event_class: DeferredEventClass,
        target_stage: DeferredTargetStageId,
    ) -> bool {
        matches!(
            (event_class, target_stage),
            (
                DeferredEventClass::DeferredSpatialEvent,
                DeferredTargetStageId::TargetResolution
            ) | (
                DeferredEventClass::DeferredCombatEvent,
                DeferredTargetStageId::PreMitigation
            )
        )
    }

    pub fn try_new(
        target_stage: DeferredTargetStageId,
        event_class: DeferredEventClass,
        source_entity_id: TEntityId,
        ready_tick: u64,
        sort_key: u64,
        payload: TPayload,
    ) -> Result<Self, DeferredEventError> {
        if Self::is_current_profile_pair_valid(event_class, target_stage) {
            Ok(Self {
                target_stage,
                event_class,
                source_entity_id,
                ready_tick,
                sort_key,
                payload,
            })
        } else {
            Err(DeferredEventError::InvalidClassTargetPair {
                event_class,
                target_stage,
            })
        }
    }

    pub fn spatial(
        source_entity_id: TEntityId,
        ready_tick: u64,
        sort_key: u64,
        payload: TPayload,
    ) -> Self {
        Self {
            target_stage: DeferredTargetStageId::TargetResolution,
            event_class: DeferredEventClass::DeferredSpatialEvent,
            source_entity_id,
            ready_tick,
            sort_key,
            payload,
        }
    }

    pub fn combat(
        source_entity_id: TEntityId,
        ready_tick: u64,
        sort_key: u64,
        payload: TPayload,
    ) -> Self {
        Self {
            target_stage: DeferredTargetStageId::PreMitigation,
            event_class: DeferredEventClass::DeferredCombatEvent,
            source_entity_id,
            ready_tick,
            sort_key,
            payload,
        }
    }

    pub fn admission_key(&self) -> (u64, DeferredTargetStageId, u64) {
        (self.ready_tick, self.target_stage, self.sort_key)
    }
}

#[cfg(test)]
mod tests {
    use std::vec::Vec;

    use super::{DeferredEvent, DeferredEventClass, DeferredEventError};
    use crate::{DeferredTargetStageId, DispatchStageId, PipelineStageId, StageIdError};

    #[test]
    fn pipeline_stage_decodes_all_twelve_values() {
        assert_eq!(
            PipelineStageId::try_from(2),
            Ok(PipelineStageId::IntentValidation)
        );
        assert_eq!(
            PipelineStageId::try_from(12),
            Ok(PipelineStageId::ObserverScopedPayloadEmission)
        );
    }

    #[test]
    fn dispatch_stage_rejects_stage_two() {
        assert_eq!(
            DispatchStageId::try_from(2),
            Err(StageIdError::InvalidDispatchStage(2))
        );
    }

    #[test]
    fn pipeline_to_dispatch_rejects_intent_validation() {
        assert_eq!(
            DispatchStageId::try_from(PipelineStageId::IntentValidation),
            Err(StageIdError::InvalidDispatchStage(2))
        );
    }

    #[test]
    fn deferred_target_stage_rejects_non_profile_stage() {
        assert_eq!(
            DeferredTargetStageId::try_from(11),
            Err(StageIdError::InvalidDeferredTargetStage(11))
        );
    }

    #[test]
    fn spatial_constructor_sets_stage_and_class() {
        let event = DeferredEvent::spatial(10_u64, 101, 5, 99_u32);
        assert_eq!(event.target_stage, DeferredTargetStageId::TargetResolution);
        assert_eq!(event.event_class, DeferredEventClass::DeferredSpatialEvent);
    }

    #[test]
    fn combat_constructor_sets_stage_and_class() {
        let event = DeferredEvent::combat(10_u64, 101, 5, 99_u32);
        assert_eq!(event.target_stage, DeferredTargetStageId::PreMitigation);
        assert_eq!(event.event_class, DeferredEventClass::DeferredCombatEvent);
    }

    #[test]
    fn invalid_pair_is_rejected() {
        let result = DeferredEvent::try_new(
            DeferredTargetStageId::TargetResolution,
            DeferredEventClass::DeferredCombatEvent,
            10_u64,
            101,
            5,
            99_u32,
        );

        assert_eq!(
            result,
            Err(DeferredEventError::InvalidClassTargetPair {
                event_class: DeferredEventClass::DeferredCombatEvent,
                target_stage: DeferredTargetStageId::TargetResolution,
            })
        );
    }

    #[test]
    fn admission_key_sorts_deterministically() {
        let mut events = Vec::from([
            DeferredEvent::combat(1_u64, 12, 9, 0_u8),
            DeferredEvent::spatial(1_u64, 11, 3, 0_u8),
            DeferredEvent::spatial(1_u64, 12, 1, 0_u8),
        ]);

        events.sort_by_key(|event| event.admission_key());

        let keys: Vec<_> = events.iter().map(|event| event.admission_key()).collect();
        assert_eq!(
            keys,
            Vec::from([
                (11, DeferredTargetStageId::TargetResolution, 3),
                (12, DeferredTargetStageId::TargetResolution, 1),
                (12, DeferredTargetStageId::PreMitigation, 9),
            ])
        );
    }
}
