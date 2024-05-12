function (doc) {
    if (doc.type === "document")
        emit(doc._id, null);
}
