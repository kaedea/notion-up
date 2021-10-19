# MarkDown Test Page - SPA

```
[notion-down-properties]
Title = 增量静态检查（SPA）在代码合入检查里的应用
Date = 2018-04-01
Published = true
Category = 
Tag = 
FileLocate = devops
FileName = incremental-spa
```

静态程序分析，是指在不运行程序的情况下分析检查代码里存在的问题。这项技术在代码质量、漏洞扫描等领域有广泛的使用。常见分析工具包括 CheckStyle、Lint、FindBugs 等，也有商用的 Coverity。本文主要讲述为我们在 Android 项目 Merge Request 合入检查里对静态程序分析技术的应用，核心内容是增量代码的静态分析方案，至于各种检查工具的对比筛选，请参考文末提供的 References。

## **名词解释**

1. 静态程序分析：SPA (Static Program Analysis)，也称静态代码检查、静态扫描、静态检查等（下文统称 “静态检查”）
2. 代码合入检查：泛指代码提交进主干分支前的一些列检查流程，比较有代表性的是 GitHub PR (Pull Request) 或者 GitLab MR (Merge Request) 合并前进行自动化检查流水线、或者 Code Review 工作（下文统称 “静态检查”，指 MR 合并前的代码检查）

## **问题背景**

微信相关 Android 项目的 DevOps 实践中，我们在合入检查方向已经先后完成了 “需求合法性检查”、“代码冲突检查”、“编译检查”、“编译后 WeTest 自动化 UI 测试” 等检查项目，代码合入检查流程已经比较完善。接下来，我们想尝试在检查流程里加入静态检查环节，看看能不能在 “统一代码风格、提高代码质量” 方面实现一些突破。

传统上，代码风格检查普遍比较依赖于人工的 Code Review，而 DevOps 实践给我们的经验是，代码格式、一般向代码错误等问题交给工具自动化处理比较合适，人工 Review 的主要目的应该是项目方案评审，以及优秀代码学习，不然的话 Code Review 很可能会变成政治任务，流于形式。因此，我们希望借助静态检查工具，先过滤大部分的一般代码问题，再交由人工进行代码设计方面的 Review 或者学习（注意，本文侧重于静态检查工具的使用，至于具体 Code Review 标准、流程请参考其他文献）。

静态检查对 Code Review 起到一个支撑作用：

> 先由静态检查工具过滤常见的错误，工具无法判断的问题可以给出先 warning log，人工 Review 再根据静态检查的 log，重点排查可疑代码
> 

不过实际应用上，静态检查工具的接入还是存在许多麻烦的问题，特别是对于一些比较成熟、历史包袱严重的项目。一方面，我们相信有不少人已经尝试过使用一些静态检查工具，这些工具在一些小项目上，经常一下子就能跑出一大堆问题，而对于比较庞大的项目，扫描出太多问题基本相当于扫描不出问题，所以我们不得不想办法让检查工具专注于我们关心的问题。另一方面，一般的静态检查工具的分析过程都比较耗时，少则几分钟，一些需要依赖编译产物的工具耗时可能达到十几分钟（类似 Coverity 这种商业功能需要依赖多维度的数据作为数据流分析的依据，耗时更是可能达到小时的级别），这种量级的时间要求对合入检查流程来说是不可接受的，特别是封版前这种时间十分紧迫的版本阶段，更不用说我们的最终目标是希望在用户本地开发代码阶段就把检查流程添加进来，因此在这个流程上我们需要对静态检查工具的性能提一个非常高的要求。

总结一下问题，现在摆在我们面的主要有 “两个矛盾”：

> 静态检查通常会检查出大量的 “陈年老代码” 带来的历史遗留问题，而这些问题大部分没人维护，也不能随意修改；而合入检查则要求只检查出新增代码带来的新问题静态检查耗时普遍比较 “可观”，越是要求检查精准，越是需要更多耗时；而静态检查则要求越快越好
> 

## **解决思路**

### **1. 如何让静态检查工具只检查出新增部分代码带来的问题**

介绍我们的方案之前，先说一说两个使用得比较普遍的方案：其一，根据代码提交的时间（例如 git 工具就可以检查每一行代码最近的时间），约定一个起始点时间（比如上一个稳定版本）作为 baseline，静态检查工具检查出来的问题，其对应的代码提交记录如果早于这个 baseline 则自动忽略该问题，这样就能从一大堆问题里面筛选出比较 “新鲜” 的问题。其二，选一个稳定版本作为 baseversion，扫描出这个版本所有的问题并把结果记录下来，以后每次静态扫描都和前面 baseversion 保留的记录做比对，屏蔽存量问题（或者直接编写脚本，根据 baseversion 扫描出来的结果，给全部存量问题自动加上 suppression 注释以便后续静态检查在扫描阶段就屏蔽问题）。

公司内部部分静态扫描服务使用的就是以上两个方案之一（比如 CodeCC 使用的是 baseversion 方案），这样做的好是思路清晰接入点也简单，几乎对于所有的静态检查工具都可以使用这些方案，也不用担心静态检查工具版本升级带来的兼容性问题。不过缺点也是显而易见的，首先是依然要重复检查老问题，白白浪费资源，而且有些新问题结果表现可能和老问题一样，导致这些问题会被当成老问题忽视。

再来说说我们现在使用的方案：DevOps 实践中，我们需要计算出用户改了哪些代码或文件（也就是用户提交的 “增量代码”），用来检查用户的行为是否合法（比如改了不允许修改的问题，或者动了别人的代码需要 @owner 过来 Review），因此我们首先想到的是可以直接利用这些增量代码，在静态检查结果中匹配出增量代码带来的问题，这样虽然无法一下解决检查效率的问题，但是也能保证匹配出来的问题大概率是和用户改动的代码相关的。再做进一步思考，既然我们已经得到代码的增量数据，我们是不是可以直接对这部分增量的代码做静态检查？这样既不用重复检查那一大堆成年老问题，也可以直接暴露出增量代码带来的问题。答案是肯定的，我们最终采取了这两种方式结合的思路：

> 直接对增量代码做检查得到一批问题报告，再从中匹配出增量代码带来的问题。
> 

### **2. 如何提高静态检查的效率**

静态检查的效率，一方面跟扫描的文件数量相关，另一方面也受工具自身扫描算法、扫描内容、检测规则的粒度、规则的数量等影响。想要提高效率，一方面我们需要尽量减少输入的文件数，而我们上面提到的增量检查思路刚好把这个方面的问题做到最优解。另一方面，至于扫描算法，自己开发更加高效的检查工具显然不太现实，所以我们把目光放到扫描内容和检测规则，好在现在主流的静态检查工具，其检查规则甚至检查粒度，大都支持用户自定义。简单地说，针对源码类型做扫描的工具比如 CheckStyle 和 Lint，需要经过词法分析、语法分析生成抽象语法树，再遍历抽象语法树跟定义的检测规则去匹配，其工作效率会比较高；而像针对 .class 字节码文件做扫描的工具 FindBugs，需要先编译源码成 .class 文件，再通过 BCEL 分析字节码指令并与探测器规则匹配，效率就会大打折扣（Lint 也支持这种检查方式，这里不做展开）。除了以上谈到的两点外，像 Android 这种 Gradle 项目，如果项目 Module 比较多，Gradle Configure 阶段也会需要比较多的耗时。

实际上，第一个问题的解决思路，已经给现在这个问题指明了一个方向：针对增量代码做检查，既减少输入文件，又降低需要执行检查任务的 Module 数。万事俱备，接下来的事就是选用合适的静态检查工具了。

对于我们的项目，目标是 “统一代码风格、提高代码质量”。统一风格方面，CheckStyle 当仁不让， 它支持直接对代码源文件进行扫描，并且内置许多成熟的 Style Guides/Conventions 方案（比如 Google/Sun/Oracle），而且自定义规则也非常简单，完全可以自定义自己的代码格式和变量命名规则。剩下的就是如何提高代码质量，我们选用的是 Lint，理由非常简单，Lint 是 Android 官方深度定制工具，和 Android 项目相性最好，功能极其强大，且可定制性和扩展性以及全面性都表现均超乎我们期待。平时编写代码过程中，Android Stuido 智能标注的各种红色（Error）、黄色（Warning）警告，大部分都是 Lint 检查的结果（所以有事没事推荐大家多按 F2 试试，自动跳到下一处 Lint 检查出问题的地方）。除了跟 IDE/Gradle 插件相结合得很好之外，Lint 也像 CheckStyle 一样，支持直接对代码源文件、甚至 XML 资源文件进行检查，不需要计算依赖或者 API References，效率比较理想。而且 Lint 自定义检查规则的功能也非常强大，几乎覆盖对大部分 Java 代码、XML 资源格式的检查。

我们的整体方案是：

> 计算增量代码以增量代码涉及的源文件作为输入（粒度是文件），给项目相关 Module 配置相应的 CheckStyle 和 Lint 任务运行检查任务，根据预置的检查规则进行扫描，得到检查结果从检查结果中筛选出和增量代码相关的问题（粒度是文件修改行数）
> 

## **具体方案实现**

### **1. 通过 git 计算增量代码的信息**

在计算代码增量信息方面，我们需要解决以下几个问题：

> 需要计算本地修改代码的增量信息，在体检代码前检查一下有没有新增问题需要计算提交 MR 时，开发分支与主干分支之间代码的增量信息，用于检查 MR 带来的新增问题当用户 MR 检查出问题后在本地修改代码，我们需要计算出 “开发分支与主干分支之间代码的增量信息” 叠加 “用户新修改问题带来的增量信息” 后的最终结果，以便用户检查自己是否已把问题修复
> 

我们计算代码增量信息的方案，全靠 `git diff` 命令：

![https://kaedea.com/assets/images/spa/img-git-diff.png](https://kaedea.com/assets/images/spa/img-git-diff.png)

这里先简单介绍一下我们方案需要用到的这几个参数的作用：

1. `name-only`：只显示修改文件的名字，不显示内容，这个参数分别刚好满足上面提到的方案的 “文件粒度” 和“文件修改行数粒度”
2. `-cached`：只显示被 staged 过的文件（也就是已经被 add 到 git index 里），计算本地修改代码的时候，需要通过这个参数计算 “已 staged” 和“未 staged”两种文件的综合数据
3. `-diff-filter=ACMR`： 显示哪类文件：Added (A)、Copied (C)、 Modified (M)、Renamed (R)，具体配置请参看官方文档
4. `-ignore-space-at-eol`: 忽略行尾空格或者换行符等修改信息，这里额外说明一下，MR 计算代码修改信息用的也是 git diff 工具而且默认不带这个参数，而 IDEA 的 Annotate 默认是带这个参数的，所以有时候会看到有人提交 MR 显示修改了大量代码（比如批量代码格式化导致修改文件换行符），而当事人本地 IDEA 又看不出自己改了代码
5. `M100%`：这是一个阈值，用来计算前后两个不同名字的文件，内容相似度达到哪个百分比就认为这是一个被 Renamed (R) 的文件

关于参数解释，这里推荐一个工具 [explainshell.com](https://explainshell.com/explain?cmd=git+diff+--name-only+--cached+--diff-filter%3DACMR+--ignore-space-at-eol+-M100%25)，不在赘述。现在回答上面提到的几个问题。

对第一个问题，通过 `git diff --diff-filter=ACMR --ignore-space-at-eol -M100%` 和 `git diff --cached --diff-filter=ACMR --ignore-space-at-eol -M100%` 两个命令组合起来，可以综合计算出本地变动代码的增量信息。至于第二个问题，可以先通过 `git merge-base <main_branch_revision> HEAD` 计算出当前分支跟主干分支之间的共同节点 merge_base_revision，再通过 `git diff <merge_base_revision> HEAD`，就可以计算出当前开发分支从主干分支拉出来之后的代码变动情况。

这个方案里最难也最容易被忽略的是第三个问题，不像第一个问题里只要分别计算 staged 和 unstaged 两种文件再加起来就完事了，这里的本地的修改数据不是简单的叠加问题：用户修改了个文件 X，代码提交后，开发分支和主干之间就有一份确定的文件 X 的修改信息 A，这时候用户在本地继续修改文件 X，那本地修改记录里文件 X 也有另一份修改信息 B，这时候 B 跟 A 的修改信息是完全冲突的，我们要的是用户修改文件后本地文件最终状态跟主干之间的代码差异 C，而 A 跟 B 都是错误的信息，而且很明显 C ≠ A + B。

为了解决第三个问题，我们前后设计了两套方案：

1. 计算增量信息的时候，先 `git add -A && git commit` 自动提交本地修改代码，然后计算 `git merge-base <main_branch_revision> HEAD`，最后 `git reset --soft HEAD~1` 把自动提交撤销掉。更详细的操作，还可以先计算修改文件哪些是 staged 的，reset 之后需要把 staged 状态恢复，全面还原文件状态。
2. 依次计算修改信息 A 和修改信息 B，遍历修改信息 B 的每一行文件修改内容，然后一次拓扑更新 A 的内容，直到遍历完全 B，这时候拓扑后的 A 就是目标的信息 C 了。

方案 1 的好处就是逻辑清晰，但是提交和撤销动作涉及本地文件修改，容易出现文件修改冲突破坏现场。方案 2 逻辑和算法都比 1 要复杂得多，好在经过几次迭代后我们证明这个路子是可行，现在稳定投产中。

作为补充说明，`git diff` 命令输出的格式不太适合直接参与后面的计算工作，需要先转换成程序友好的格式（比如 JSON），这里推荐一款基于 Python 的 git diff 解析工具：[git-diff-parser](https://github.com/nathforge/gitdiffparser)。项目中我们采用的是 Gradle 插件，所以也用 Groovy 实现了类似的解析工作。假设我们修改了 `MainActivity.java` 文件，新增了 `basepacks.txt` 文件，`git diff` 解析前格式是：

```
diff --git a/app/src/main/java/com/example/app/MainActivity.java b/app/src/main/java/com/example/app/MainActivity.java
index d3151dd..80ba56b 100644
--- a/app/src/main/java/com/example/app/MainActivity.java
+++ b/app/src/main/java/com/example/app/MainActivity.java
@@ -7,6 +7,8 @@ import android.widget.Toast;

 import com.jianghongkui.customelint.R;

+import java.io.IOException;
+
 public class MainActivity extends AppCompatActivity {

     @Override
@@ -15,11 +17,26 @@ public class MainActivity extends AppCompatActivity {
         setContentView(R.layout.activity_main);

-         Toast.makeText(this, "", 20);
-         assert true;
+        Toast.makeText(this, "", 20);
+        assert true;
+        String hello = "hello";
+        System.out.println(hello);
+        Integer.parseInt("2");
+        Float.parseFloat("2");
+        System.loadLibrary("hello");
+        try {
+            getAssets().open("hello");
+        } catch (IOException e) {
+            e.printStackTrace();
+        }
+
+        foo("hello2");
+        foo("libandromeda");
+        System.out.println("libflutter");
+        System.out.println("libflutter_v7.so");
+    }

-         System.out.println("hello");
-         Integer.parseInt("2");
-         Float.parseFloat("2");
+    private void foo(String str) {
+        System.loadLibrary(str);
     }
 }
diff --git a/add.txt b/add.txt
new file mode 100644
index 0000000..9b07058
--- /dev/null
+++ b/add.txt
@@ -0,0 +1,2 @@
+asad
+asdasd
\ No newline at end of file

```

经过解析之后变成：

```
[
    {
        "file": "app/src/main/java/com/example/app/MainActivity.java",
        "changed_lines": [
            10,
            11,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
            33,
            34,
            35,
            36,
            37,
            39,
            40
        ],
        "deleted_lines": [
            18,
            19,
            21,
            22,
            23
        ],
        "is_new_file": false
    },
    {
        "file": "add.txt",
        "changed_lines": [
            1,
            2
        ],
        "deleted_lines": [],
        "is_new_file": true
    }
]

```

具体代码请参考文末提供的代码仓库。

### **2. 基于 AGP 插件的 Lint 增量检查方案**

在增量检查的具体实现上，我们采用的是自定义 Gradle 插件，增加了 `:checkIncremental` 任务来执行增量的检查任务。其中 CheckStyle 检查的实现是基于 Gradle Api 提供相关 Checkstyle Task，这个本身就支持增量检查，直接配置输入文件就好。Lint 的增量检查就要复杂得多，主要是基于 Android 官方的 AGP (Android Gradle Plugin) 插件提供的 `com.android.tools.lint:lint-gradle` 库进行实现，以下介绍几个关键的技术点。

### **Lint 检查的工作流程**

Android Lint 的工作过程比较简单，由一个基础的 Lint 过程由 Lint Tool（检测工具），Source Files（项目源文件） 和 lint.xml（配置文件） 三个部分组成：Lint Tool 读取 Source Files，根据 lint.xml 配置的规则（issue）输出结果，如下图：

![https://kaedea.com/assets/images/spa/image-lint-workflow.png](https://kaedea.com/assets/images/spa/image-lint-workflow.png)

Android 项目中，一般我们有三种方式运行 啊走Lint 检查：命令行、IDEA 的 Inspections 检查功能、Gradle Lint 任务，他们都由 [AGP Android Lint](http://tools.android.com/tips/lint) 提供，并由 Android 官方进行维护，虽然检查入口各不相同，但是底层都是同一套 Lint API 实现（提供 Lint 检查实现的 lint-api.jar 和封装好一些常用检查规则的 lint-check.jar，三种工作方式都是基于这两个类库实现）。

届于 Lint API 涉及的类库比较复杂，这里不做深入讨论，主要介绍一下几个比较关键的 API：

1. `LintDriver`: 三种工作方式最后都通过 LintDriver#analyse() 执行实际上的检查工作。
2. `IssueRegistry`：管理 Lint 检查规则，配合 lint.xml 使用。Android 有内置的 BuiltinIssueRegistry，用户自定义检查的话，需要重写该类。
3. `LintRequest`：执行 Lint 检查时的一个请求类，封装好了需要检查的文件内容，我们需要实现的增量检查，也是要从这里下手。
4. `LintClient`：Lint 客户端，集成 Lint 检查的操作、配置，对应某一种具体的工作方式，比如 LintCliClient 对应命令行方式，LintIdeClient 对应 IDEA 的 Inspections，LintGradleClient 对应 Gradle Lint Task。

用伪代码表示的话大概是：

```
def registry = new IssueRegistry()
def client = new LintClient(registry) {
    override createLintRequest(file) {
        return new LintRequest(file)
    }
    override run() {
        LintDriver.analyze()  // super impl
    }
}
client.run()

```

### **Lint 自定义检查规则**

自定义检查规则，就是要自定义各种检查 Detector 类，具体可以参考官方的指导文档 [Writing a Lint Check](http://tools.android.com/tips/lint/writing-a-lint-check) 或者美团的几篇 Lint 实践文章 [美团 Lint](https://tech.meituan.com/tags/lint.html)。老实说，这方面官方给出的 Example 并不是很详细，具体怎么写还是要靠自己去看官方 Lint API 的源码，以及参考别人的开源代码（如果你比较熟悉 Visitor 访问者模式，或者写过 ASM 插件，应该比较容易上手）。

这里给出一个我们自己自定义的检查规则作参考：

```
// 检查 Log 的使用规范
public class LogIssue extends Detector implements Detector.UastScanner {

    public static final Issue ISSUE = Issue.create(
            "WxLog",
            "Log 使用不规范, 请使用 platformtools.Log",
            "请使用项目共用的Log函数, 输出console及xlog文件请使用platformtools.Log, 不希望输出xlog文件请使用android.util.Log",
            Category.CORRECTNESS,
            9,
            Severity.ERROR,
            new Implementation(LogIssue.class, Scope.JAVA_FILE_SCOPE));

    @Override
    public void visitMethod(@NotNull JavaContext context, @NotNull UCallExpression node, @NotNull PsiMethod method) {
        if (context.getEvaluator().isMemberInClass(method, "java.io.PrintStream")) {
            context.report(ISSUE, context.getLocation(node), ISSUE.getBriefDescription(TextFormat.TEXT));
        }
    }

    @Override
    public List<String> getApplicableMethodNames() {
        return Arrays.asList("print", "println");
    }
}

```

### **Lint 增量检查的实现方案**

上面提到，“我们需要实现的增量检查，需要从 LintRequest 下手”，通过重写 LintClient 中的 createLintRequest 方法，传入我们需要增量检查的文件，以下给出关键的代码，具体的实现细节，请参考我们的代码库。

```
class LintToolClient extends LintCliClient {

    @Override
    protected LintRequest createLintRequest(List<File> files) {
        LintRequest request = super.createLintRequest(files)
        for (Project project : request.getProjects()) {
            for (File file : files) {
                project.addFile(file) // 具体需要检查的文件
            }
        }
        return new LintRequest(this, files)
    }
}

```

上面提到有三种 Lint 的工作方式，我们采用的是扩展第三种 Lint Gradle 方式（因为这种方式能直接复用现成的 lint.xml 配置文件和 Lint Output 报告格式），最终整体的工作流程是：

> 通过 git diff 获得需要检查文件作为 Source Files。根据自己的检查需要自定义 LintIssueRegistry（增加了一批自定义的 Detector，考虑的性能需要，移除了那些需要依赖编译产物的内置 Detectors）。自定义继承 LintGradleClient 的 LintIncrementalClient（也就是采用 Lint Gradle 工作方式）。根据 Source Files，为每一个有文件变动的 Module 创建增量检查用的 Gradle Task；运行检查任务的时候，执行 LintIncrementalClient#run() 实现增量检查
> 

除了我们采用的第三种 Lint Gradle 方式，这里补充说明一下第二种 IDEA 的 Inspections 功能：通过 “IDEA - Analyse - Inspect Code” 可以迅速针对一个指定的文件做 Lint 检查。如下：

![https://kaedea.com/assets/images/spa/image-idea-inspect-code.png](https://kaedea.com/assets/images/spa/image-idea-inspect-code.png)

经过挖掘，我们发现其实现的关键代码在 [LintIdeClient.java](https://github.com/JetBrains/android/blob/master/android/src/com/android/tools/idea/lint/LintIdeClient.java)。通过 Inspections 方案，我们能直接对指定文件进行 Lint 检查，而不需要依赖于 Gradle 环境，这是 Lint 增量检查的最佳方案。不过考虑到 IDEA 版本之间的兼容性问题，而且我们还需要将检查工作合入到 DevOps 自动化流程里，所以最终还是选择了 Gradle Lint 方案。

最后，关于具体的 Lint 实现有一点需要补充说明：Lint API 25 到 26 之间，无论是 API 接口还是具体的实现，变化都非常大，所以各位参考别人的具体实现代码的时候，一定要先分清当前的 API 版本是多少。

### **3. 整体工作流程图**

没有流程图的方案是没有灵魂的，如下：

![https://kaedea.com/assets/images/spa/image-workflows.png](https://kaedea.com/assets/images/spa/image-workflows.png)

## **结果沉淀**

以代码仓库的 Demo 项目为例，如果执行一遍默认的 `:app:clean :app:lint` 检查任务，耗时 Configure + 检查任务整体耗时大概在 10s 左右，如下：

![https://kaedea.com/assets/images/spa/image-demo-1.png](https://kaedea.com/assets/images/spa/image-demo-1.png)

接入增量 Lint 方案后，耗时已经能压缩到 1s 左右：

![https://kaedea.com/assets/images/spa/image-demo-1.png](https://kaedea.com/assets/images/spa/image-demo-1.png)

即使加上增量的 CheckStyle 检查任务，再最终补上一个用来做检查结果报告的 `checkReport` 任务，整体增量检查耗时也能稳定在 1s：

![https://kaedea.com/assets/images/spa/image-demo-1.png](https://kaedea.com/assets/images/spa/image-demo-1.png)

在实际项目 MR 合入检查流水线里的应用效果如下：

在 MR 代码合入检查的静态检查环节上，我们目前一共实现了 CheckStyle、Lint、文件格式（LF/CRLF 换行符问题）、非法文件修改（文件权限）四种检查内容，其中 Lint 增量带来的收益最明显，时间成本从原本的几分钟、十几分钟级别下降到几秒到几十秒的级别（通常只要在封版前涉及大量代码修改的 MR 才需要几十秒的耗时），已经基本满足了我们 DevOps 合入检查的要求（考虑到静态检查环节是我们合入检查几个并行的 Stages 之间耗时最小的一个，可以说相当于没有时间成本）。而且除了时间成本之外，Lint 自定义检查的功能相当于给我们的平台提供了一种定制性比较强的检查工具，比如 Dark Mode 对 XML 的颜色值有使用规范，通过自定义 Detector 可以很轻松得检查每一个新增 XML 文件的 color 属性。

## **尾巴**

本文主要以介绍静态检查整体的应用方案为主，以及分享方案落地流程里一些问题，主要是一己的经验之谈。如果你希望了解现有静态检查工具的对比和应用，这方面市场上已经有大量的科普和评测文章请自行检索，如果你希望试用各种检查工具，这里推荐一下公司内部的静态检查服务 CodeCC 和 CodeDog，他们都有详细的使用文档。又或者你想研究 Lint API 具体的工作细节，这里推荐一下美团技术团队编写的几篇 Lint 相关技术文章 [美团 Lint](https://tech.meituan.com/tags/lint.html)。

## **参考链接**

1. [http://tools.android.com/tips/lint](http://tools.android.com/tips/lint) （官方文档）
2. [https://tech.meituan.com/tags/lint.html](https://tech.meituan.com/tags/lint.html) （美团 Lint 实践）
3. [https://www.jianshu.com/p/a0f28fbef73f](https://www.jianshu.com/p/a0f28fbef73f) （自定义 Lint 规则）
4. [https://blog.csdn.net/ouyang_peng/article/details/80374867](https://blog.csdn.net/ouyang_peng/article/details/80374867) （自定义 Lint 规则）
5. [https://www.jianshu.com/p/4833a79e9396](https://www.jianshu.com/p/4833a79e9396) （增量 Lint 实现）
6. [https://github.com/lingochamp/okcheck](https://github.com/lingochamp/okcheck) （增量检查，粒度是有代码改动的 Module，一个折中的方案，优点是侵入性小)