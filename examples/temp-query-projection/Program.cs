using FreeSql;
using FreeSql.DataAnnotations;
using System.Linq.Expressions;
using System.Text.Json;

try
{
    int count = 23;
    bool baseline = false;
    for (int i = 0; i < args.Length; i++)
    {
        if (args[i] == "--baseline") baseline = true;
        else if (args[i] == "--count" && i + 1 < args.Length
            && int.TryParse(args[++i], out int n) && n is >= 0 and <= 1000) count = n;
        else throw new ArgumentException("Usage: TempProjection [--count 0..1000] [--baseline]");
    }

    SQLitePCL.Batteries_V2.Init();
    using var db = new FreeSqlBuilder()
        .UseConnectionString(DataType.Sqlite, "Data Source=:memory:")
        .UseAutoSyncStructure(true)
        .Build();
    db.CodeFirst.SyncStructure(typeof(CaseInfo), typeof(CaseExtendInfo), typeof(SysUserInfo), typeof(CaseProcInfo), typeof(CaseProcSchedule));
    db.Insert(new[] {
        new CaseInfo { Id = "case-1", CaseTypeId = "X", CaseName = "文档", Volume = "V-1", UndertakeDeptId = "D-1" },
        new CaseInfo { Id = "case-other", CaseTypeId = "Y", CaseName = "excluded", Volume = "V-2", UndertakeDeptId = "D-2" }
    }).ExecuteAffrows();
    db.Insert(new CaseExtendInfo { CaseId = "case-1", EstimatedRiskFee = 12.5m }).ExecuteAffrows();
    db.Insert(new[] {
        new SysUserInfo { UserId = "user-1", DeptId = "D-1" },
        new SysUserInfo { UserId = "user-2", DeptId = "D-2" }
    }).ExecuteAffrows();
    db.Insert(new[] {
        new CaseProcInfo { ProcId = "proc-1", CaseId = "case-1", CtrlProcId = "CTRL", ProcStatusId = "ready", UndertakeUserId = "user-1", ProjectSchedule = .75m },
        new CaseProcInfo { ProcId = "proc-alt", CaseId = "case-1", CtrlProcId = "CTRL-alt", ProcStatusId = null, UndertakeUserId = "user-1", ProjectSchedule = null },
        new CaseProcInfo { ProcId = "proc-type", CaseId = "case-other", UndertakeUserId = "user-1" },
        new CaseProcInfo { ProcId = "proc-user", CaseId = "case-1", UndertakeUserId = "user-2" }
    }).ExecuteAffrows();
    var records = Enumerable.Range(0, count).Select(i => new CaseProcSchedule {
        ScheduleId = $"s-{i:D2}", CreateTime = new DateTime(2026, 10, 1).AddDays(i),
        FillingTime = new DateTime(2026, 10, 1), ProcId = i % 2 == 0 ? "proc-1" : "proc-alt",
        Progress = i % 2 == 0 ? i : null, CostDays = i + .5m, ScheduleDetail = "detail " + i
    }).ToList();
    records.AddRange(new[] {
        new CaseProcSchedule { ScheduleId = "skip-type", ProcId = "proc-type", FillingTime = new DateTime(2026, 10, 1), ScheduleDetail = "preserve type" },
        new CaseProcSchedule { ScheduleId = "skip-user", ProcId = "proc-user", FillingTime = new DateTime(2026, 10, 1), ScheduleDetail = "preserve user" },
        new CaseProcSchedule { ScheduleId = "skip-date", ProcId = "proc-1", FillingTime = new DateTime(2026, 9, 1), ScheduleDetail = "preserve date" }
    });
    db.Insert(records).ExecuteAffrows();

    object Snapshot() => db.Select<CaseProcSchedule>().OrderBy(s => s.ScheduleId).ToList(s => new {
        s.ScheduleId, s.ProcId, s.CreateTime, s.FillingTime, s.Progress, s.CostDays, s.ScheduleDetail
    });
    var sourceBefore = Snapshot();
    var sql = new List<string>();
    bool observe = true;
    db.Aop.CurdBefore += (_, e) => { if (observe) sql.Add(e.Sql); };

    // Both operations use the same expression, selecting fields present in the temporary query.
    Expression<Func<CaseProcSchedule, ProductivityInfo>> projection = s => new ProductivityInfo {
        CreateTime = s.CreateTime, ScheduleId = s.ScheduleId, ProcId = s.ProcId,
        CaseId = s.ProcInfo!.CaseInfo!.Id,
        ProgressMonth = s.FillingTime!.Value.Year + "年" + s.FillingTime.Value.Month + "月",
        ProgressValue = s.Progress ?? 0, ScheduleDetail = s.ScheduleDetail,
        ContributionRatio = s.ProcInfo!.ProjectSchedule, Volume = s.ProcInfo!.CaseInfo!.Volume,
        CaseName = s.ProcInfo!.CaseInfo!.CaseName, UndertakeDepartment = s.ProcInfo!.CaseInfo!.UndertakeDeptId,
        ProcName = s.ProcInfo!.CtrlProcId, ProcStatus = s.ProcInfo!.ProcStatusId ?? "",
        Undertaker = s.ProcInfo!.UndertakeUserId ?? "", ProgressCostDays = s.CostDays,
        EstimatedRiskFee = s.ProcInfo!.CaseInfo!.ExtendInfo!.EstimatedRiskFee
    };
    var listRows = await Query(db).ToListAsync(projection);
    var chunks = new List<List<ProductivityInfo>>();
    await foreach (var batch in Query(db).ToChunkAsyncEnumerable(baseline ? UnprojectedMember() : projection, 10)
        .WithCancellation(CancellationToken.None)) chunks.Add(batch);
    observe = false;
    var sourceAfter = Snapshot();

    // Generate SQL only. A connection attempt is deliberately forbidden.
    using var sqlServer = new FreeSqlBuilder()
        .UseConnectionFactory(DataType.SqlServer, () => throw new InvalidOperationException("SQL Server execution is not part of this example"))
        .UseAutoSyncStructure(false)
        .Build();
    string sqlServerSql = Query(sqlServer).ToSql(projection);
    Console.WriteLine(JsonSerializer.Serialize(new {
        ListRows = listRows, Chunks = chunks, SourceBefore = sourceBefore, SourceAfter = sourceAfter,
        ExecutedSql = sql, SqlServerGeneratedOnly = true, SqlServerSql = sqlServerSql
    }));
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine(error.GetType().Name + ": " + error.Message);
    return 2;
}

static ISelect<CaseProcSchedule> Query(IFreeSql db)
{
    DateTime[] months = [new DateTime(2026, 10, 1)];
    string[] innerUsers = ["user-1"];
    string[] outerUsers = ["user-1"];
    var source = db.Select<CaseProcSchedule>();
    // SQL Server lock hints belong on the inner source, before WithTempQuery.
    if (db.Ado.DataType == DataType.SqlServer) source = source.WithLock();
    return source
        .InnerJoin(s => s.ProcId == s.ProcInfo!.ProcId)
        .InnerJoin(s => s.ProcInfo!.CaseId == s.ProcInfo!.CaseInfo!.Id)
        .Where(s => s.ProcInfo!.CaseInfo!.CaseTypeId == "X")
        .Where(s => months.Contains(s.FillingTime!.Value))
        .Where(s => innerUsers.Contains(s.ProcInfo!.UndertakeUserId!))
        .WithTempQuery(s => new CaseProcSchedule {
            ScheduleId = s.ScheduleId, CreateTime = s.CreateTime, FillingTime = s.FillingTime,
            ProcId = s.ProcId, Progress = s.Progress, CostDays = s.CostDays, ScheduleDetail = s.ScheduleDetail,
            ProcInfo = new CaseProcInfo {
                ProcId = s.ProcInfo!.ProcId, CtrlProcId = s.ProcInfo!.CtrlProcId,
                ProcStatusId = s.ProcInfo!.ProcStatusId, ProjectSchedule = s.ProcInfo!.ProjectSchedule,
                UndertakeUserId = s.ProcInfo!.UndertakeUserId,
                UndertakeUserInfo = new SysUserInfo { UserId = s.ProcInfo!.UndertakeUserInfo!.UserId, DeptId = s.ProcInfo!.UndertakeUserInfo!.DeptId },
                CaseInfo = new CaseInfo {
                    Id = s.ProcInfo!.CaseInfo!.Id, CaseName = s.ProcInfo!.CaseInfo!.CaseName,
                    Volume = s.ProcInfo!.CaseInfo!.Volume, UndertakeDeptId = s.ProcInfo!.CaseInfo!.UndertakeDeptId,
                    ExtendInfo = new CaseExtendInfo { CaseId = s.ProcInfo!.CaseInfo!.ExtendInfo!.CaseId, EstimatedRiskFee = s.ProcInfo!.CaseInfo!.ExtendInfo!.EstimatedRiskFee }
                }
            }
        }).Where(s => outerUsers.Contains(s.ProcInfo!.UndertakeUserId!)).OrderBy(s => s.ScheduleId);
}

// The path used in the original chunk snippet was not included in WithTempQuery.
static Expression<Func<CaseProcSchedule, ProductivityInfo>> UnprojectedMember() => s => new ProductivityInfo {
    CaseId = s.ProcInfo!.CaseId
};

[Table(Name="case_info")] public class CaseInfo {
    [Column(Name="case_id", IsPrimary=true)] public string Id { get; set; } = "";
    [Column(Name="case_type_id")] public string CaseTypeId { get; set; } = "";
    [Column(Name="case_name")] public string CaseName { get; set; } = "";
    [Column(Name="volume")] public string Volume { get; set; } = "";
    [Column(Name="undertake_dept_id")] public string UndertakeDeptId { get; set; } = "";
    [Navigate(nameof(Id))] public CaseExtendInfo? ExtendInfo { get; set; }
}
[Table(Name="case_extend_info")] public class CaseExtendInfo {
    [Column(Name="case_id", IsPrimary=true)] public string CaseId { get; set; } = "";
    [Column(Name="estimated_risk_fee")] public decimal EstimatedRiskFee { get; set; }
}
[Table(Name="sys_user_info")] public class SysUserInfo {
    [Column(Name="user_id", IsPrimary=true)] public string UserId { get; set; } = "";
    [Column(Name="dept_id")] public string DeptId { get; set; } = "";
}
[Table(Name="case_proc_info")] public class CaseProcInfo {
    [Column(Name="proc_id", IsPrimary=true)] public string ProcId { get; set; } = "";
    [Column(Name="case_id")] public string CaseId { get; set; } = "";
    [Column(Name="ctrl_proc_id")] public string CtrlProcId { get; set; } = "";
    [Column(Name="proc_status_id")] public string? ProcStatusId { get; set; }
    [Column(Name="project_schedule")] public decimal? ProjectSchedule { get; set; }
    [Column(Name="undertake_user_id")] public string? UndertakeUserId { get; set; }
    [Navigate(nameof(UndertakeUserId))] public SysUserInfo? UndertakeUserInfo { get; set; }
    [Navigate(nameof(CaseId))] public CaseInfo? CaseInfo { get; set; }
}
[Table(Name="case_proc_schedule")] public class CaseProcSchedule {
    [Column(Name="schedule_id", IsPrimary=true)] public string ScheduleId { get; set; } = "";
    [Column(Name="create_time")] public DateTime CreateTime { get; set; }
    [Column(Name="filling_time")] public DateTime? FillingTime { get; set; }
    [Column(Name="proc_id")] public string ProcId { get; set; } = "";
    [Column(Name="progress")] public decimal? Progress { get; set; }
    [Column(Name="cost_days")] public decimal CostDays { get; set; }
    [Column(Name="schedule_detail")] public string ScheduleDetail { get; set; } = "";
    [Navigate(nameof(ProcId))] public CaseProcInfo? ProcInfo { get; set; }
}
public record ProductivityInfo {
    public DateTime CreateTime { get; init; }
    public string ScheduleId { get; init; } = "";
    public string ProcId { get; init; } = "";
    public string CaseId { get; init; } = "";
    public string ProgressMonth { get; init; } = "";
    public decimal ProgressValue { get; init; }
    public string ScheduleDetail { get; init; } = "";
    public decimal? ContributionRatio { get; init; }
    public string Volume { get; init; } = "";
    public string CaseName { get; init; } = "";
    public string UndertakeDepartment { get; init; } = "";
    public string ProcName { get; init; } = "";
    public string ProcStatus { get; init; } = "";
    public string Undertaker { get; init; } = "";
    public decimal ProgressCostDays { get; init; }
    public decimal EstimatedRiskFee { get; init; }
}
