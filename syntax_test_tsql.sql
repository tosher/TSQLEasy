-- SYNTAX TEST "Packages/TSQLEasy/TSQL.sublime-syntax"

set @gibrddapietanigiro = convert(bigint,
-- <- keyword.other.DML.sql
--  ^ variable.sql
--                      ^ keyword.operator.comparison.sql
--                        ^ keyword.other.reserved.sql
--                                ^ storage.type.sql
    CAST(substring(convert(binary(4), @rddapietanigiro), 4, 1) AS binary(1)) +
--       ^ support.function.string.sql
--                                                             ^ keyword.other.reserved.sql
    CAST(substring(convert(binary(4), @rddapietanigiro), 3, 1) as binary(1)) +
--                                                             ^^ keyword.other.reserved.sql
--                                                                           ^ keyword.operator.math.sql
    CAST(substring(convert(binary(4), @rddapietanigiro), 2, 1) AS binary(1)) +
    CAST(substring(convert(binary(4), @rddapietanigiro), 1, 1) AS binary(1)))

SELECT name FROM sysdatabases WHERE name = 'Automation'
--                                         ^ punctuation.definition.string.begin.sql
--                                          ^^^^^ string.quoted.single.sql
--                                                    ^ punctuation.definition.string.end.sql

set @gibrddapietanigiro = case when @gibrddapietanigiro < 0 then @gibrddapietanigiro + 4294967296 else @gibrddapietanigiro end
-- <- keyword.other.DML.sql
--                        ^ keyword.other.DML.sql

/*
set @gibrddapietanigiro = case when @gibrddapietanigiro < 0 then @gibrddapietanigiro + 4294967296 else @gibrddapietanigiro end
--                               ^^^^^^^^^^^^^^^^^ comment.block.c.sql
*/
 --  <- punctuation.definition.comment.sql

select top 1
-- <- keyword.other.DML.sql
--     ^ keyword.other.reserved.sql
  @tnuoccaecivresetanigiroid = sa.ID
from tnuoccaecivres sa with(nolock),
  tnuoccapi as ipa with(nolock),
--           ^ keyword.alias-as.other.sql
  tsoh h,
  tsohredivorp ph
--             ^ source.tsql
where sa.epyttnuoccaecivresid in (2, 12)
  and ipa.ID = sa.ID
  and h.ID = ipa.tsohredivorpid
  and ph.ID = ipa.tsohredivorpid
--    ^^ entity.name.alias.sql
--            ^^ entity.name.alias.sql
  --and (h.IPAddr & ph.mask) = (@rddapietanigiro & ph.mask)
--           ^ comment.line.double-dash.sql
  and @gibrddapietanigiro between ph.piwol and ph.pihgih
-- ^ keyword.other.DML.sql
--       ^ variable.sql
  and (sa.epyttnuoccaecivresid = 12 or ipa.tsohid is null or ipa.tsohid = @tsohid)
--                               ^^ constant.numeric.sql
--                                                   ^^^^ constant.language.sql
  and sa.sutats < 4
order by ph.pihgih - ph.piwol


select *,
  sa.ID as SAID
from TNUoccaecIVRes sa,
  left outer join TNUoccApi as ipa on ipa.saID = sa.ID,
--                          ^^ keyword.alias-as.other.sql
--                                 ^^ keyword.alias-as.on.other.sql
--                                     ^ entity.name.alias.sql
--                                               ^^ entity.name.alias.sql
  tsoh h,
--     ^ source.tsql
-- TODO: yes, not entity.name.alias.sql
  tsohredivorp as ph
--                ^ entity.name.alias.sql
