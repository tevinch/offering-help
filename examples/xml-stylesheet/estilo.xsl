<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" doctype-system="about:legacy-compat"/>
  <xsl:template match="/ficha">
    <html lang="en">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>Sample grade report</title>
        <style>
          body { margin: 0; color: #202c3a; background: #f4f6f8; font: 16px/1.5 system-ui, sans-serif; }
          main { max-width: 72rem; margin: auto; padding: 1.5rem; }
          h1 { margin-bottom: .25rem; }
          h2 { font-size: 1.2rem; margin: 1.75rem 0 .5rem; }
          .sample { color: #52616e; }
          .table-scroll { overflow-x: auto; border: 1px solid #cbd4dc; background: white; }
          table { width: 100%; border-collapse: collapse; text-align: left; font: inherit; }
          th, td { padding: .6rem .75rem; border-bottom: 1px solid #dce2e7; vertical-align: top; }
          th { background: #e9eef3; }
          tbody tr:last-child td { border-bottom: 0; }
          caption { text-align: left; font-weight: 600; padding: .6rem .75rem; }
          dl { display: flex; flex-wrap: wrap; gap: 1rem 2rem; }
          dt { font-weight: 600; } dd { margin: 0; }
          .summary { background: #e5f0e8; padding: .75rem 1rem; }
          .notice { padding-left: 1.25rem; }
          @media (max-width: 36rem) { main { padding: 1rem; } th, td { padding: .5rem; } }
        </style>
      </head>
      <body>
        <main>
          <header>
            <p class="sample">Synthetic data · XML + a separate stylesheet</p>
            <h1>Sample grade report</h1>
            <dl id="student">
              <div><dt>Name</dt><dd><xsl:value-of select="studentHeader/name"/></dd></div>
              <div><dt>Example identifier</dt><dd><xsl:value-of select="studentHeader/account"/></dd></div>
              <div><dt>Generated</dt><dd><xsl:value-of select="studentHeader/dateReport"/></dd></div>
            </dl>
          </header>
          <section aria-labelledby="homework-heading">
            <h2 id="homework-heading">Homework</h2>
            <div class="table-scroll">
              <table id="homework">
                <caption>Homework results</caption>
                <thead><tr><th scope="col">Number</th><th scope="col">Due date</th><th scope="col">Score</th><th scope="col">Comment</th><th scope="col">Late days</th></tr></thead>
                <tbody>
                  <xsl:for-each select="tarea">
                    <tr><td><xsl:value-of select="numero"/></td><td><xsl:value-of select="fechaEnt"/></td><td><xsl:value-of select="calif"/></td><td><xsl:value-of select="comentario"/></td><td><xsl:value-of select="extemp"/></td></tr>
                  </xsl:for-each>
                </tbody>
              </table>
            </div>
          </section>
          <section aria-labelledby="papers-heading">
            <h2 id="papers-heading">Papers</h2>
            <div class="table-scroll">
              <table id="papers">
                <caption>Paper results</caption>
                <thead><tr><th scope="col">Number</th><th scope="col">Due date</th><th scope="col">Score</th><th scope="col">Group</th><th scope="col">Topic 1</th><th scope="col">Topic 2</th><th scope="col">Comment</th></tr></thead>
                <tbody>
                  <xsl:for-each select="trabajo">
                    <tr><td><xsl:value-of select="numero"/></td><td><xsl:value-of select="fechaEnt"/></td><td><xsl:value-of select="calif"/></td><td><xsl:value-of select="equipo"/></td><td><xsl:value-of select="tema1"/></td><td><xsl:value-of select="tema2"/></td><td><xsl:value-of select="comentario"/></td></tr>
                  </xsl:for-each>
                </tbody>
              </table>
            </div>
          </section>
          <section aria-labelledby="exams-heading">
            <h2 id="exams-heading">Exams</h2>
            <div class="table-scroll">
              <table id="exams">
                <caption>Exam results</caption>
                <thead><tr><th scope="col">Exam</th><th scope="col">Date</th><th scope="col">Score</th><th scope="col">Comment</th></tr></thead>
                <tbody>
                  <xsl:for-each select="examen">
                    <tr><td><xsl:value-of select="numero"/></td><td><xsl:value-of select="fechaEnt"/></td><td><xsl:value-of select="calif"/></td><td><xsl:value-of select="comentario"/></td></tr>
                  </xsl:for-each>
                </tbody>
              </table>
            </div>
          </section>
          <section aria-labelledby="summary-heading">
            <h2 id="summary-heading">Summary</h2>
            <dl class="summary" id="summary">
              <div><dt>Homework</dt><dd><xsl:value-of select="calif/ta"/></dd></div>
              <div><dt>Papers</dt><dd><xsl:value-of select="calif/tr"/></dd></div>
              <div><dt>Exams</dt><dd><xsl:value-of select="calif/ex"/></dd></div>
              <div><dt>Extra</dt><dd><xsl:value-of select="calif/extra"/></dd></div>
              <div><dt>Final score</dt><dd id="final-score"><xsl:value-of select="calif/nota"/></dd></div>
            </dl>
          </section>
          <section aria-labelledby="notices-heading">
            <h2 id="notices-heading">Notices</h2>
            <ul class="notice" id="notices">
              <xsl:for-each select="nota">
                <li><strong><xsl:value-of select="numero"/> · <xsl:value-of select="fechaEnt"/>: </strong><xsl:value-of select="comentario"/></li>
              </xsl:for-each>
            </ul>
          </section>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
