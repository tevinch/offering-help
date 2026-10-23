using Csla;

namespace AsyncDataReader;

[Serializable]
public sealed class PersonInfo : ReadOnlyBase<PersonInfo>
{
    public static readonly PropertyInfo<int> IdProperty = RegisterProperty<int>(nameof(Id));
    public int Id => GetProperty(IdProperty);

    public static readonly PropertyInfo<string?> NameProperty = RegisterProperty<string?>(nameof(Name));
    public string? Name => GetProperty(NameProperty);

    public static readonly PropertyInfo<string?> NicknameProperty = RegisterProperty<string?>(nameof(Nickname));
    public string? Nickname => GetProperty(NicknameProperty);

    [FetchChild]
    private void Fetch(PersonRow row)
    {
        LoadProperty(IdProperty, row.Id);
        LoadProperty(NameProperty, row.Name);
        LoadProperty(NicknameProperty, row.Nickname);
    }
}

[Serializable]
public sealed class PersonList : ReadOnlyListBase<PersonList, PersonInfo>
{
    [Fetch]
    private async Task Fetch(string prefix, [Inject] IPersonDal dal,
        [Inject] IChildDataPortal<PersonInfo> children)
    {
        var rows = await dal.FetchAsync(prefix);
        using (LoadListMode)
            foreach (var row in rows)
                Add(children.FetchChild(row));
    }
}
