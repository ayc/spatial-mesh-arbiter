#![no_std]

#[cfg(test)]
extern crate std;

mod deferred_event;
mod stage;

pub use deferred_event::{DeferredEvent, DeferredEventClass, DeferredEventError};
pub use stage::{DeferredTargetStageId, DispatchStageId, PipelineStageId, StageIdError};

pub type EntityId = u64;
