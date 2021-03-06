# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Support for suppressing and soloing logging to console per thread.
- `TypedStruct`: Support for inheritance.
- `EasyMeta`: the `before_subclass_init` hook.
- `wait` and `iter_wait` support `log_interval` and `log_level` for printing
  the thrown `PredicateNotSatisfied` to the log.
- `takesome`: a new generator that partially yields a sequence
- `repr` and `hash` to typed struct fields.

### Fixed
- `ExponentialBackoff`: return the value **before** the incrementation.
- `concurrent`: capture `KeyboardInterrupt` exceptions like any other.
- doctests in various functions and classes.
- `SynchronizedSingleton` on `contextmanager` deadlock when some (but not all)
  of the CMs throw.
- `resilient` between `timecache`s bug.

### Changed
- Reorganization:
  - Moved tokens to a proper module.
  - Moved function from `easypy.concurrency` and `easypy.timing` to new module
    `easypy.sync`
  - Moved `throttled` from `easypy.concurrency` to `easypy.timing`.
- `easypy.signals`: Async handlers are invoked first, then the sequential handlers.
- `async` -> `asynchronous`: to support python 3.7, where this word is reserved

### Removed
- `Bunch`: The rigid `KEYS` feature.
- `synchronized_on_first_call`.
- `ExponentialBackoff`: The unused `iteration` argument.
- `easypy.cartesian`
- `easypy.selective_queue`
- `easypy.timezone`

### Deprecated
- `locking_lru_cache`.

## [0.2.0] - 2018-11-15
### Added
- Add the `easypy.aliasing` module.
- Add the `easypy.bunch` module.
- Add the `easypy.caching` module.
- Add the `easypy.cartesian` module.
- Add the `easypy.collections` module.
- Add the `easypy.colors` module.
- Add the `easypy.concurrency` module.
- Add the `easypy.contexts` module.
- Add the `easypy.decorations` module.
- Add the `easypy.exceptions` module.
- Add the `easypy.fixtures` module.
- Add the `easypy.gevent` module.
- Add the `easypy.humanize` module.
- Add the `easypy.interaction` module.
- Add the `easypy.lockstep` module.
- Add the `easypy.logging` module.
- Add the `easypy.meta` module.
- Add the `easypy.misc` module.
- Add the `easypy.mocking` module.
- Add the `easypy.predicates` module.
- Add the `easypy.properties` module.
- Add the `easypy.randutils` module.
- Add the `easypy.resilience` module.
- Add the `easypy.selective_queue` module.
- Add the `easypy.signals` module.
- Add the `easypy.tables` module.
- Add the `easypy.threadtree` module.
- Add the `easypy.timezone` module.
- Add the `easypy.timing` module.
- Add the `easypy.typed_struct` module.
- Add the `easypy.units` module.
- Add the `easypy.words` module.
- Add the `easypy.ziplog` module.
