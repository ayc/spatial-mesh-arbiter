use core::fmt;

/// Errors returned when decoding raw numeric stage identifiers.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StageIdError {
    InvalidPipelineStage(u8),
    InvalidDispatchStage(u8),
    InvalidDeferredTargetStage(u8),
}

impl fmt::Display for StageIdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            StageIdError::InvalidPipelineStage(value) => {
                write!(f, "invalid PipelineStageId value: {value}")
            }
            StageIdError::InvalidDispatchStage(value) => {
                write!(f, "invalid DispatchStageId value: {value}")
            }
            StageIdError::InvalidDeferredTargetStage(value) => {
                write!(f, "invalid DeferredTargetStageId value: {value}")
            }
        }
    }
}

/// The full conceptual 12-stage authoritative pipeline.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum PipelineStageId {
    ControlAuthorityAndInputRouting = 1,
    IntentValidation = 2,
    TargetResolution = 3,
    PreKinematic = 4,
    KinematicResolution = 5,
    PostKinematic = 6,
    PreMitigation = 7,
    DamageResolution = 8,
    PostDamage = 9,
    DeathCheck = 10,
    StateUpdate = 11,
    ObserverScopedPayloadEmission = 12,
}

impl TryFrom<u8> for PipelineStageId {
    type Error = StageIdError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            1 => Ok(Self::ControlAuthorityAndInputRouting),
            2 => Ok(Self::IntentValidation),
            3 => Ok(Self::TargetResolution),
            4 => Ok(Self::PreKinematic),
            5 => Ok(Self::KinematicResolution),
            6 => Ok(Self::PostKinematic),
            7 => Ok(Self::PreMitigation),
            8 => Ok(Self::DamageResolution),
            9 => Ok(Self::PostDamage),
            10 => Ok(Self::DeathCheck),
            11 => Ok(Self::StateUpdate),
            12 => Ok(Self::ObserverScopedPayloadEmission),
            _ => Err(StageIdError::InvalidPipelineStage(value)),
        }
    }
}

impl From<PipelineStageId> for u8 {
    fn from(value: PipelineStageId) -> Self {
        value as u8
    }
}

/// The subset of stages accepted by the `dispatch_stage` hook.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum DispatchStageId {
    ControlAuthorityAndInputRouting = 1,
    TargetResolution = 3,
    PreKinematic = 4,
    KinematicResolution = 5,
    PostKinematic = 6,
    PreMitigation = 7,
    DamageResolution = 8,
    PostDamage = 9,
    DeathCheck = 10,
    StateUpdate = 11,
    ObserverScopedPayloadEmission = 12,
}

impl DispatchStageId {
    pub const fn ordered() -> [Self; 11] {
        [
            Self::ControlAuthorityAndInputRouting,
            Self::TargetResolution,
            Self::PreKinematic,
            Self::KinematicResolution,
            Self::PostKinematic,
            Self::PreMitigation,
            Self::DamageResolution,
            Self::PostDamage,
            Self::DeathCheck,
            Self::StateUpdate,
            Self::ObserverScopedPayloadEmission,
        ]
    }
}

impl TryFrom<u8> for DispatchStageId {
    type Error = StageIdError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            1 => Ok(Self::ControlAuthorityAndInputRouting),
            3 => Ok(Self::TargetResolution),
            4 => Ok(Self::PreKinematic),
            5 => Ok(Self::KinematicResolution),
            6 => Ok(Self::PostKinematic),
            7 => Ok(Self::PreMitigation),
            8 => Ok(Self::DamageResolution),
            9 => Ok(Self::PostDamage),
            10 => Ok(Self::DeathCheck),
            11 => Ok(Self::StateUpdate),
            12 => Ok(Self::ObserverScopedPayloadEmission),
            _ => Err(StageIdError::InvalidDispatchStage(value)),
        }
    }
}

impl From<DispatchStageId> for u8 {
    fn from(value: DispatchStageId) -> Self {
        value as u8
    }
}

impl From<DispatchStageId> for PipelineStageId {
    fn from(value: DispatchStageId) -> Self {
        match value {
            DispatchStageId::ControlAuthorityAndInputRouting => {
                PipelineStageId::ControlAuthorityAndInputRouting
            }
            DispatchStageId::TargetResolution => PipelineStageId::TargetResolution,
            DispatchStageId::PreKinematic => PipelineStageId::PreKinematic,
            DispatchStageId::KinematicResolution => PipelineStageId::KinematicResolution,
            DispatchStageId::PostKinematic => PipelineStageId::PostKinematic,
            DispatchStageId::PreMitigation => PipelineStageId::PreMitigation,
            DispatchStageId::DamageResolution => PipelineStageId::DamageResolution,
            DispatchStageId::PostDamage => PipelineStageId::PostDamage,
            DispatchStageId::DeathCheck => PipelineStageId::DeathCheck,
            DispatchStageId::StateUpdate => PipelineStageId::StateUpdate,
            DispatchStageId::ObserverScopedPayloadEmission => {
                PipelineStageId::ObserverScopedPayloadEmission
            }
        }
    }
}

impl TryFrom<PipelineStageId> for DispatchStageId {
    type Error = StageIdError;

    fn try_from(value: PipelineStageId) -> Result<Self, Self::Error> {
        match value {
            PipelineStageId::ControlAuthorityAndInputRouting => {
                Ok(DispatchStageId::ControlAuthorityAndInputRouting)
            }
            PipelineStageId::IntentValidation => Err(StageIdError::InvalidDispatchStage(
                PipelineStageId::IntentValidation as u8,
            )),
            PipelineStageId::TargetResolution => Ok(DispatchStageId::TargetResolution),
            PipelineStageId::PreKinematic => Ok(DispatchStageId::PreKinematic),
            PipelineStageId::KinematicResolution => Ok(DispatchStageId::KinematicResolution),
            PipelineStageId::PostKinematic => Ok(DispatchStageId::PostKinematic),
            PipelineStageId::PreMitigation => Ok(DispatchStageId::PreMitigation),
            PipelineStageId::DamageResolution => Ok(DispatchStageId::DamageResolution),
            PipelineStageId::PostDamage => Ok(DispatchStageId::PostDamage),
            PipelineStageId::DeathCheck => Ok(DispatchStageId::DeathCheck),
            PipelineStageId::StateUpdate => Ok(DispatchStageId::StateUpdate),
            PipelineStageId::ObserverScopedPayloadEmission => {
                Ok(DispatchStageId::ObserverScopedPayloadEmission)
            }
        }
    }
}

/// The currently valid set of deferred re-entry targets.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum DeferredTargetStageId {
    TargetResolution = 3,
    PreMitigation = 7,
}

impl TryFrom<u8> for DeferredTargetStageId {
    type Error = StageIdError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            3 => Ok(Self::TargetResolution),
            7 => Ok(Self::PreMitigation),
            _ => Err(StageIdError::InvalidDeferredTargetStage(value)),
        }
    }
}

impl From<DeferredTargetStageId> for u8 {
    fn from(value: DeferredTargetStageId) -> Self {
        value as u8
    }
}

impl From<DeferredTargetStageId> for PipelineStageId {
    fn from(value: DeferredTargetStageId) -> Self {
        match value {
            DeferredTargetStageId::TargetResolution => PipelineStageId::TargetResolution,
            DeferredTargetStageId::PreMitigation => PipelineStageId::PreMitigation,
        }
    }
}
