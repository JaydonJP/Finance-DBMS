"""Build the DA3 submission PDF from source, real screenshots and test evidence.

Run with the Codex bundled Python (reportlab, Pillow and pypdf), or install those
three packages in a separate document environment. The app itself needs none.
"""
import json
from pathlib import Path
from html import escape
import textwrap

from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.enums import TA_LEFT

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'submission'
E=json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
WIDTH,HEIGHT=612,792
BODY=ParagraphStyle('Body',fontName='Helvetica',fontSize=10.5,leading=15,textColor=colors.black,spaceAfter=9)
SMALL=ParagraphStyle('Small',parent=BODY,fontSize=8.8,leading=12)
CODE=ParagraphStyle('Code',parent=BODY,fontName='Courier',fontSize=8,leading=11)
H1=ParagraphStyle('Heading',parent=BODY,fontName='Helvetica-Bold',fontSize=20,leading=25)
H2=ParagraphStyle('Subheading',parent=BODY,fontName='Helvetica-Bold',fontSize=12,leading=17)


class Report:
    def __init__(self):
        self.c=canvas.Canvas(str(OUT/'DA3_Report.pdf'),pagesize=(WIDTH,HEIGHT))
        self.c.setTitle('Personal Finance and Investment Relationship Analysis using Neo4j')
        self.c.setAuthor('Personal Finance DBMS DA3')
        self.page=0
        self.y=0
    def next(self,title):
        if self.page:
            self.c.showPage()
        self.page+=1
        self.c.setFillColor(colors.black)
        self.c.setFont('Helvetica',8)
        self.c.drawString(48,756,'DATABASE SYSTEMS  |  DA3 IMPLEMENTATION REPORT')
        self.c.drawRightString(564,36,str(self.page))
        self.y=714
        self.p(title,H1,after=18)
    def p(self,text,style=BODY,after=9):
        para=Paragraph(text,style)
        _,height=para.wrap(516,700)
        if self.y-height<54:
            raise RuntimeError(f'Page {self.page} overflow near {text[:60]}')
        para.drawOn(self.c,48,self.y-height)
        self.y-=height+after
    def sub(self,text):
        self.p(text,H2,after=7)
    def code(self,text):
        lines=[]
        for line in text.splitlines():
            lines.extend(textwrap.wrap(line,96,replace_whitespace=False,drop_whitespace=False) or [''])
        self.p('<br/>'.join(escape(x).replace(' ','&nbsp;') for x in lines),CODE,after=13)
    def table(self,headers,rows,widths):
        data=[[Paragraph(escape(str(v)),ParagraphStyle('cellhead',parent=SMALL,fontName='Helvetica-Bold')) for v in headers]]
        data += [[Paragraph(escape(str(v)),SMALL) for v in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        commands=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9edf0')),
            ('GRID',(0,0),(-1,-1),.5,colors.HexColor('#d9d9d9')),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),
            ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6)]
        t.setStyle(TableStyle(commands))
        _,height=t.wrap(516,700)
        if self.y-height<54:
            raise RuntimeError(f'Table does not fit page {self.page}: {height}, y={self.y}')
        t.drawOn(self.c,48,self.y-height)
        self.y-=height+15
    def image(self,name,width=516,maxheight=400):
        path=OUT/'screenshots'/name
        with PILImage.open(path) as image:
            w,h=image.size
        factor=min(width/w,maxheight/h)
        w,h=w*factor,h*factor
        if self.y-h<54:
            raise RuntimeError(f'Figure does not fit page {self.page}')
        self.c.drawImage(str(path),48+(516-w)/2,self.y-h,width=w,height=h)
        self.y-=h+12


r=Report()
r.next('Personal Finance and Investment Relationship Analysis')
r.p('Using Neo4j Community Edition',ParagraphStyle('Subtitle',parent=H1,fontSize=17,leading=22),after=17)
r.p('DA3 Mini Project Report<br/>Database category Graph Database<br/>Submission date 20 October 2026',BODY,after=18)
for label,name in [('Student name','student_name'),('Registration number','registration_number'),('Faculty name','faculty_name')]:
    r.c.setFont('Helvetica',10)
    r.c.drawString(48,r.y-12,label)
    r.c.acroForm.textfield(name=name,tooltip=label,x=195,y=r.y-18,width=369,height=20,
        fontName='Helvetica',fontSize=10,borderStyle='underlined',borderWidth=.5,
        borderColor=colors.HexColor('#888888'),fillColor=colors.white,textColor=colors.black)
    r.y-=33
r.y-=13
r.sub('Abstract')
r.p('This project extends an Oracle based personal finance mini project using Neo4j, a property graph database. '
    'It retains households, users, accounts, banks, companies, investments, subscriptions, savings goals and ledger records. '
    'Explicit graph relationships enable employer and investment overlap, household company exposure and shared investment queries. '
    'A Flask application provides complete record management, an interactive graph explorer and fifteen Cypher reports.')
r.p('The implementation stores monetary values as integer paise and groups ledger changes, balance adjustments and audit snapshots '
    'in atomic managed transactions. Real database integration tests verify CRUD, rollback, concurrency and persistence. '
    'Neo4j is justified for connected analysis; the comparison recognizes the strengths of relational databases for ledger integrity and reporting.')
r.sub('Report contents')
r.p('Application and database choice; graph schema; dataset and integrity; browser implementation; Cypher reports; graph query results; '
    'visual demonstration; verification; comparison; setup and references.',SMALL)

r.next('Application and database choice')
r.sub('Problem and objectives')
r.p('Personal finance information is spread across people, accounts, employers and investment holdings. The DA2 implementation uses '
    'Oracle tables, SQL reports and PL/SQL programs. DA3 implements the same domain in Neo4j and explores connections that a tabular dashboard does not show directly.')
r.p('The objectives are to design a property graph, import the original fictional data, implement core operations, demonstrate '
    'technology specific queries and explain the suitability and limitations of the selected database.')
r.sub('Why Neo4j')
r.p('Neo4j represents entities as labeled nodes, typed directed relationships and properties on both [1]. A user can belong to a household, '
    'own accounts, work for a company and hold that company\'s shares. Cypher expresses those connected patterns directly. '
    'The selected database is in the Graph Database category explicitly allowed by the assignment.')
r.p('The implementation uses Community Edition, standard Cypher and the official Python driver. It requires no paid service, '
    'embedding model, graph plugin or external API for normal operation. Graph insights are explainable through returned paths.')
r.sub('Alternatives considered')
r.table(['Option','Suitability assessment for this project'],[
    ['Time series database','Useful for a workload centered on dense historical measurements; this extension prioritizes relationships across existing entities.'],
    ['Vector database','Would require a semantic similarity use case and an embedding pipeline beyond the current structured finance data.'],
    ['Column family database','A distributed ingestion or partition scale requirement is not established by this small classroom workload.'],
    ['Distributed SQL','Could retain SQL and relational structure; it would demonstrate less of the selected relationship modeling change.'],
    ['Neo4j graph database','Matches the chosen connected analysis and provides visible nodes, relationships and Cypher paths.']
],[130,386])
r.p('These are project design judgments, not general rankings or performance benchmarks. SQL can also answer the selected questions using joins.',SMALL)

r.next('Property graph schema')
r.p('Ten business node labels retain the original conceptual entities. Share ownership becomes a relationship with a quantity property. '
    'AuditEvent supports history; DemoState supports import state and serialized application writes.')
# Purpose-built schema diagram, rendered as vector shapes and text in the PDF.
cx=r.c; top=r.y
positions={'Household':(90,top-45),'User':(270,top-45),'Company':(480,top-45),
           'Bank':(90,top-160),'Account':(270,top-160),'Share':(480,top-160),
           'Category':(90,top-265),'Transaction':(270,top-265),'Goal':(480,top-265)}
def link(a,b,label,dy=0):
    x,y=positions[a];xx,yy=positions[b]
    cx.setStrokeColor(colors.HexColor('#a0a9af'));cx.line(x,y,xx,yy)
    cx.setFillColor(colors.black);cx.setFont('Helvetica',7.2);cx.drawCentredString((x+xx)/2,(y+yy)/2+dy+6,label)
for a,b,label,dy in [('User','Household','MEMBER_OF',0),('User','Company','WORKS_AT',0),('User','Account','OWNS',0),
    ('Account','Bank','HELD_AT',0),('Company','Share','ISSUES',0),('User','Share','HOLDS quantity',-9),
    ('Account','Transaction','HAS_TRANSACTION',0),('Transaction','Category','IN_CATEGORY',0),('Account','Goal','HAS_GOAL',-12)]:
    link(a,b,label,dy)
for label,(x,y) in positions.items():
    cx.setFillColor(colors.HexColor('#eef1f3'));cx.setStrokeColor(colors.HexColor('#b8c3c9'));cx.roundRect(x-43,y-16,86,32,5,fill=1,stroke=1)
    cx.setFillColor(colors.black);cx.setFont('Helvetica-Bold',9);cx.drawCentredString(x,y-3,label)
r.y=top-305
r.p('Figure 1. Main graph schema. Arrow direction is specified by the relationship definitions below. Subscription and audit records are omitted from the drawing for readability.',SMALL)
r.table(['Relationship','Direction and meaning'],[
    ['MEMBER_OF and WORKS_AT','User to Household; User to Company'],
    ['OWNS and HELD_AT','User or Company to Account; Account to Bank'],
    ['ISSUES and HOLDS','Company to Share; User to Share, with quantity and pair key'],
    ['HAS_TRANSACTION and IN_CATEGORY','Account to Transaction; Transaction or Goal to Category'],
    ['HAS_GOAL and HAS_SUBSCRIPTION','Account to Goal; Account to Subscription']
],[195,321])
r.p('IDs have unique key properties. Subscription keys combine account and subscription IDs. Audit events retain transaction IDs and old/new snapshots after a transaction is deleted.',SMALL)

r.next('Dataset and transactional integrity')
r.sub('Portable fictional sample dataset')
counts=E['counts']
r.table(['Collection','Count','Collection','Count'],[
    ['Households',counts['household'],'Companies',counts['company']],
    ['Banks',counts['bank'],'Categories',counts['category']],
    ['Users',counts['users'],'Accounts',counts['account']],
    ['Shares',counts['shares'],'Holdings relationships',counts['user_shares']],
    ['Subscriptions',counts['subscription'],'Goals',counts['goal']],
    ['Transactions',counts['transaction'],'Initial audit events',12]
],[190,68,190,68])
r.p('The data/sample.json fixture contains opening balances, not already adjusted balances. A single atomic import creates all records '
    'and applies the twelve sample transactions once. The resulting graph has 57 business nodes and 72 relationships. '
    'Twelve audit nodes and one state node bring the total stored node count to 70. Repeating import preserves existing edits.')
r.sub('Exact money and stable references')
r.p('Values entered in rupees are parsed using Decimal and stored as integer paise. For example, INR 250 is stored as 25000. '
    'Native date properties retain transaction dates and dates of birth. Unique keys prevent duplicate identifiers; '
    'application validation checks required values, allowed types, ownership, references and dependent deletion.')
r.sub('Atomic ledger algorithm')
r.code('BEGIN managed write transaction\n  Increment DemoState revision to acquire the shared write lock\n  Read old ledger entry and validate new references\n  Reverse old balance effect and apply new effect as net changes\n  Reject any resulting negative account balance\n  Persist ledger entry and permanent audit snapshot\nCOMMIT together or ROLLBACK together')
r.p('The single state lock serializes all application writes before checks or balance reads. This conservative classroom design '
    'prevents conflicting writes but limits throughput. Managed transactions are provided by the Neo4j driver [2]; '
    'locking and isolation behavior are documented by Neo4j [4].')
r.p('Account 1001 reconciles as 25000 + 50000 - 4500 - 2500 - 1200 = INR 66800. All seven accounts reconcile to their opening balances and ledgers.',SMALL)

r.next('Browser application and core operations')
r.p('The standalone Flask application runs on port 5001 and uses Waitress. A local Neo4j container stores the graph. '
    'All application queries use the official Python driver. The interface includes the overview, management screens, reports and graph explorer.')
r.image('dashboard.jpg',maxheight=335)
r.p('Figure 2. Actual overview screenshot. The baseline total account balance is INR 435300 and recorded expenses total INR 79700.',SMALL)
r.sub('Implemented operations')
r.table(['Operation','Implemented behavior'],[
    ['Create and read','All eleven original business collections, including relationships and composite keys.'],
    ['Update','Editable entity properties, relationships, holdings quantity and ledger values.'],
    ['Delete','Restricted dependent deletion; ledger deletion reverses its effect and retains audit history.'],
    ['Form protection','Server validation, parameterized queries, escaped templates and session CSRF tokens.']
],[120,396])
r.p('A real browser test submitted the new-user form and verified the success message. Its temporary user was removed after capturing evidence. Additional form screenshots are included in the submission source.',SMALL)

r.next('Cypher reports and financial queries')
r.p('The application exposes all twelve DA2 reports rewritten in Cypher and three additional graph insights. Each report shows '
    'its query and live results, with a CSV download. The complete runnable statements are in queries.cypher.')
r.table(['ID','Report','Demonstrated concept'],[
    ['Q01','Household members and ages','Relationship match and date duration'],
    ['Q02','Account owners and bank balances','Connected ownership pattern'],
    ['Q03','Investment portfolio value','Relationship properties and calculation'],
    ['Q04','Spending by category','Filtering and aggregate sum'],
    ['Q05','Accounts above average balance','Aggregation followed by filtering'],
    ['Q06','Savings goal progress','Expression and rounding'],
    ['Q07','Monthly subscription cost','CASE and cycle normalization'],
    ['Q08','Company employee counts','OPTIONAL MATCH includes zero'],
    ['Q09','Largest expense per account','Grouped maximum and matching ties'],
    ['Q10','Monthly income and expenses','Dates and conditional aggregation'],
    ['Q11','Total balances by bank','Optional links and aggregation'],
    ['Q12','Permanent transaction audit','History after ledger deletion'],
    ['G01','Employer and investment overlap','Closed connected pattern'],
    ['G02','Household company exposure','Multiple relationship traversal'],
    ['G03','Shared investment connections','Common-neighbor pattern']
],[39,227,250])
r.sub('Example category spending query')
from reports import REPORTS
r.code(REPORTS['Q04']['cypher'])
r.p('Actual expense totals are Salary 50000, Travel 12000, Utilities 7500, Food 7200 and Investment 3000 rupees. '
    'The Salary expense category follows the original company sample transaction; category and income/expense direction are separate fields.',SMALL)

r.next('Graph specific queries and results')
r.sub('Employer and investment overlap')
r.code(REPORTS['G01']['cypher'])
r.table(['Member','Employer','Investment INR'],[
    [x['member'],x['employer'],f"{x['investment_rupees']:,.2f}"] for x in E['reports']['G01']
],[150,236,130])
r.p('This pattern connects a user to an employer and to shares issued by that same employer. Four users match in the sample dataset. '
    'It identifies overlapping salary and investment exposure for exploration; it does not measure total financial risk.')
r.sub('Household company exposure')
r.code(REPORTS['G02']['cypher'])
r.table(['Household','Company','Exposure INR'],[
    [x['household'],x['company'],f"{x['exposure_rupees']:,.2f}"] for x in E['reports']['G02']
],[150,236,130])
r.p('Household exposure follows members, their HOLDS relationships and issuing companies. The result combines Rahul and Dev\'s different Nexa shares into INR 5400 for Rao Household.',SMALL)

r.next('Graph visualization and shared investments')
r.p('The explorer queries Neo4j and renders returned entities and relationships in local SVG. Users can select nodes, inspect '
    'properties, filter by household or insight, pan, zoom, fit the graph and show relationship labels. Standard Cypher graph '
    'variants also run in Neo4j Browser.')
r.image('graph-detail.jpg',width=500,maxheight=295)
r.p('Figure 3. Actual employer and investment graph. User, Company and Share labels are shown in separate columns to make the relationships easier to follow.',SMALL)
r.sub('Shared investment connections')
r.code(REPORTS['G03']['cypher'])
r.table(['User pair','Shared share'],[
    [x['member_one']+' and '+x['member_two'],', '.join(map(str,x['shared_shares']))] for x in E['reports']['G03']
],[350,166])
r.p('The baseline yields Arun Kumar with Priya Kumar through share 302 and Arun Kumar with Rahul Rao through share 301. '
    'The ordering condition returns each user pair once.',SMALL)

r.next('Verification and observed results')
r.p('Integration checks ran against the actual Neo4j instance, not an in-memory substitute. The fixture counts, report results '
    'and reconciliation evidence are stored in submission/verification.json. Temporary records are removed after testing.')
r.p('Verification timestamp '+escape(E['tested_at'])+'. Core integration run '+str(E['duration_seconds'])+' seconds. '
    'This duration is a test-run observation, not an Oracle versus Neo4j benchmark.',SMALL)
r.table(['Check','Outcome'],[[x['name'],x['status']] for x in E['checks']],[440,76])
r.sub('Important cases')
r.p('The ledger lifecycle test inserts an expense, changes its amount and type, moves it to another account and deletes it. '
    'Both account balances return to their initial values while five audit snapshots remain. Invalid references and overspending '
    'leave ledger, balance and audit counts unchanged.')
r.p('The concurrency test submits two INR 700 expenses against an account with INR 980. Exactly one commits, the other is rejected, '
    'and INR 280 remains. The temporary transactions and their test audit events are then removed.')
r.p('A stop and restart check confirms that original users, transactions and balances persist. Browser checks confirm a successful '
    'user creation, graph insight selection and node property inspection. All twelve verification groups passed.')

r.next('Comparison and limitations')
r.table(['Aspect','Oracle DA2','Neo4j DA3'],[
    ['Representation','Relational tables and foreign keys','Labeled nodes and typed relationships'],
    ['Share ownership','Junction table with quantity','HOLDS relationship with quantity'],
    ['Query language','SQL and PL/SQL','Cypher pattern matching'],
    ['Connected questions','Explicit joins or recursive queries','Relationship patterns and paths'],
    ['Balance and audit','Database trigger','Managed application write transaction'],
    ['Uniqueness','Primary and unique constraints','Node and relationship key uniqueness'],
    ['Other integrity rules','Foreign keys and CHECK constraints','Explicit validation in the application'],
    ['Visualization','Usually rows and report tables','Native graph results and path explorer'],
    ['Suitability here','Structured ledger and tabular reports','Connected household and investment analysis']
],[102,207,207])
r.sub('Advantages for the selected use case')
r.p('The graph model makes relationships first class data. Investment quantity belongs naturally to HOLDS, and queries can '
    'follow people through households, employers and investments without representing every connection as a separate joined table. '
    'Returning paths provides visible explanations for the three connected insights [1].')
r.sub('Limits and tradeoffs')
r.p('Neo4j Community supports uniqueness constraints, while several existence, type and key constraint features belong to '
    'Enterprise Edition [3]. This application therefore validates required fields and relationship cardinalities in Python. '
    'Manual Neo4j Browser writes can bypass these checks.')
r.p('The state lock serializes writes and is designed for a small educational workload. The local administration UI has no '
    'user login or authorization. Displayed graphs are bounded to 300 nodes or relationships, and household views to 200 '
    'relationships. There is no fraud model, automated investment advice or measured speed advantage over Oracle.')

r.next('Setup demonstration and references')
r.sub('Reproduce the implementation')
r.p('On Windows, install Python 3.10 or newer and Ubuntu WSL2. Extract the source ZIP into a writable directory and run '
    'Start DA3.cmd. The first run installs Python packages, prepares Podman in Ubuntu and downloads the pinned official '
    'Neo4j Community image. It creates private local credentials and imports the sample dataset. Later runs preserve data and work offline.')
r.code('Application     http://127.0.0.1:5001/\nGraph explorer  http://127.0.0.1:5001/graph\nNeo4j Browser   http://127.0.0.1:7474/\nBolt connection bolt://127.0.0.1:7687\nVerify          .venv\\Scripts\\python.exe verify.py')
r.p('The database uses persistent volume pf-da3-neo4j-data. Stop DA3.cmd stops the application and Neo4j without deleting '
    'the volume. Credentials, virtual environments and runtime files are excluded from the submission ZIP.')
r.sub('Demonstration sequence')
r.p('Show the overview and graph model; add, edit and delete a temporary user; add a 250 rupee expense to account 1001; '
    'edit it to 300; delete it and show the restored 66800 balance and permanent audit events. Run G01 to G03 and explain '
    'one equivalent SQL query. Use DEMO_GUIDE.md for exact steps and expected results.')
r.sub('Conclusion')
r.p('The mini project is implemented using a modern graph database with a reproducible dataset, complete record management, '
    'atomic ledger behavior and technology specific queries. Neo4j is suitable for the chosen relationship analysis. '
    'Oracle remains a strong option for the original relational ledger and its declarative integrity requirements.')
r.sub('References')
references=[
    ('1','Neo4j graph database concepts','https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/'),
    ('2','Neo4j Python managed transactions','https://neo4j.com/docs/python-manual/current/transactions/'),
    ('3','Cypher and Neo4j edition capabilities','https://neo4j.com/docs/cypher-manual/current/introduction/cypher-neo4j/'),
    ('4','Neo4j concurrent data access','https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/'),
    ('5','Neo4j official container setup','https://neo4j.com/docs/operations-manual/current/docker/introduction/'),
]
for n,title,url in references:
    r.p(f'[{n}] {escape(title)}<br/><link href="{url}">{escape(url)}</link>',SMALL,after=6)
r.c.save()
print('Created',OUT/'DA3_Report.pdf','with',r.page,'pages')
