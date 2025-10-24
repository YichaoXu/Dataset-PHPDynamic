---
globs: **/*design.md
alwaysApply: false
---
# Design Documentation Standards

## Required Document Structure
The following sections MUST appear in every design document:

### Design Overview
Include a class diagram showing all classes and their relationships at the beginning of the document.
**Format**: Use concise paragraph format with inline code blocks to show:
- All classes in the module
- Key relationships (inheritance, composition, dependencies)
- Abstract classes and exceptions

**Example Format**:
**Classes**: `ClassA`, `ClassB`, `ClassC`, `ClassD`
**Relationships**: `ClassA` extends `ClassB`, `ClassA` contains `ClassC`, `ClassA` uses `ClassD`
**Abstract**: `ClassE` (implemented by `ClassF`, `ClassG`)
**Exceptions**: `ExceptionH` extends `ExceptionI`, raised by `ClassA`

### Class Specifications
**[ClassName] Class** 
- **Responsibility**: [Single sentence purpose]
- **Properties**: `property: type` - Brief description
- **[method_name(param: type) -> return_type]**
  - **Behavior**: [What it does]
  - **Input**: [Parameter description]
  - **Output**: [Return description]
  - **Raises**: [Exception conditions]
- **Example Usage**: Include minimal working example
...

### Exception Classes
**[ExceptionName]**: [When raised]

### Validation Rules
**[Component] Validation**:
- [Validation rule]

---

## AI Design Guidelines (Internal Use Only)

These contents should not appear in the final product documents, as they are evident to the reader.

### Design Change Policy
- No legacy design details when design changes
- No backward compatibility requirements
- All designs can be rebuilt from scratch
- No existing component compatibility requirements

### Design Modification Restrictions
- Never modify existing design without explicit user authorization
- Preserve original design intent and structure
- Do not change return types, parameter signatures, or method behaviors without user request
- Do not add, remove, or rename methods unless explicitly instructed
- Maintain exact interface compatibility unless user specifically requests changes

### Design Principles
#### Single Responsibility
- Each class should have one reason to change
- Methods should perform a single, well-defined task
- Avoid god classes that handle multiple concerns

#### Interface Segregation
- Design focused interfaces rather than large, general-purpose ones
- Clients should not depend on interfaces they don't use
- Prefer composition over inheritance

#### Dependency Inversion
- Depend on abstractions, not concretions
- High-level modules should not depend on low-level modules
- Use dependency injection for better testability

#### Open/Closed Principle
- Open for extension, closed for modification
- Use interfaces and abstract classes for extensibility
- Avoid modifying existing code when adding new features