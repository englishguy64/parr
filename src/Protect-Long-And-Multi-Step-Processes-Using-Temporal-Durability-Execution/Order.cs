namespace TemporalApp;

// The data passed into the workflow. It is stored in the Event History, so keep it small and serialisable.
public record Order(string Id, decimal Amount);
