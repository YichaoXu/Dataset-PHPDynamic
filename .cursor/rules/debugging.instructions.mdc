---
description: Only when any errors occurred during program execution
alwaysApply: false
---
# Debugging Standards

## Internal Debugging
### Debug Logging Strategy
- Use prefixed functions for internal debugging only
- Import debugging utilities from appropriate modules
- Debug logs written to designated log files
- Not exposed in public API
- Use appropriate log levels (debug, info, warn, error)

### Debug Context Management
- Use context managers for debugging scopes
- Track execution flow and performance
- Monitor module calls and responses
- Measure operation timing

## Exception Handling
### Exception Strategy
- Use specific exception classes per module/stage
- Preserve original exception context with appropriate chaining
- Catch exceptions at appropriate abstraction level
- Provide meaningful error messages with context

### Exception Patterns
- **ModuleError**: Module-specific application logic errors
- **ValidationError**: Input validation errors
- **ConfigurationError**: Configuration-related errors
- **ResourceError**: Resource access/availability errors
- **NetworkError**: Network communication errors

## Error Handling Patterns
### Module Error Handling
- Catch module exceptions in appropriate layers
- Transform technical errors to user-friendly messages
- Use internal debugging for technical details
- Provide recovery options when possible

### UI Error Handling
- Catch exceptions in UI layer
- Display user-friendly error messages
- Use internal debugging for technical details
- Provide recovery options when possible

## Debugging Strategy
### Error Investigation
- Use exception traces to identify failure points
- Use internal debug logs for detailed flow tracking
- Check exception context for root causes
- Test error conditions explicitly

### Debugging Tools
- Use appropriate debugging tools for the language/platform
- Set breakpoints at critical points
- Use step-through debugging when needed
- Monitor memory usage and performance

## Error Recovery
### Graceful Degradation
- Handle errors gracefully without crashing
- Provide fallback mechanisms when possible
- Log errors for later analysis
- Notify users of issues when appropriate

### Error Reporting
- Collect relevant context information
- Include stack traces and error details
- Report errors to appropriate monitoring systems
- Maintain error logs for analysis

## Debugging Best Practices
### Logging Guidelines
- Use appropriate log levels
- Include relevant context information
- Avoid logging sensitive information
- Use structured logging when possible

### Error Context
- Include relevant parameters and state
- Provide clear error messages
- Include stack traces for debugging
- Maintain error context across layers

### Performance Considerations
- Avoid expensive operations in error paths
- Use asynchronous logging when possible
- Limit debug output in production
- Monitor debugging overhead

## Language-Specific Considerations
### Debugging Tools
- Use language-specific debugging tools
- Follow language-specific error handling patterns
- Use appropriate exception types
- Follow language-specific logging conventions

### Error Handling Patterns
- Use language-specific exception handling
- Follow language-specific error recovery patterns
- Use appropriate error propagation mechanisms
- Follow language-specific debugging practices