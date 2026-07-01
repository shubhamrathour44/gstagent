# ITR XML Schema Reference

Complete XML structure for Income Tax e-filing portal submissions.

---

## 📋 Schema Overview

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ITRDocument xmlns="http://www.incometaxindia.gov.in" DocumentType="ITR-1">
  <TaxableEntity>
    <PAN>ABCDE1234F</PAN>
    <Name>Raj Kumar</Name>
    <DOB>15011985</DOB>
    <Age>38</Age>  <!-- Optional, for ITR-2 -->
  </TaxableEntity>
  
  <ITRForm FormName="ITR-1" AY="2023-24">
    <IncomeDetails>
      <!-- Income elements -->
    </IncomeDetails>
    
    <Deductions>
      <!-- Deduction elements -->
    </Deductions>
    
    <TaxComputation>
      <!-- Tax details -->
    </TaxComputation>
    
    <TaxPaid>
      <!-- TDS and advance tax -->
    </TaxPaid>
    
    <Verification>
      <!-- Digital signature (if verified) -->
    </Verification>
  </ITRForm>
</ITRDocument>
```

---

## 📊 ITR-1 Schema

### **Mandatory Fields**

```xml
<IncomeDetails>
  <SalaryIncome>1000000.00</SalaryIncome>
  <HRAExemption>300000.00</HRAExemption>
  <StandardDeduction>50000.00</StandardDeduction>
  <IncomeFromHouseProperty>0.00</IncomeFromHouseProperty>
  <InterestIncome>0.00</InterestIncome>
  <OtherIncome>0.00</OtherIncome>
  <GrossTotalIncome>650000.00</GrossTotalIncome>
</IncomeDetails>

<Deductions>
  <Section80C>150000.00</Section80C>
  <Section80D>0.00</Section80D>
  <Section80E>0.00</Section80E>
  <Section80G>0.00</Section80G>
  <Section80TTA>0.00</Section80TTA>
  <TotalDeductions>150000.00</TotalDeductions>
</Deductions>

<TaxComputation>
  <TaxableIncome>500000.00</TaxableIncome>
  <IncomeTax>12500.00</IncomeTax>
  <Surcharge>0.00</Surcharge>
  <Cess>0.00</Cess>
  <TotalTax>12500.00</TotalTax>
</TaxComputation>

<TaxPaid>
  <TDSEmployer>15000.00</TDSEmployer>
  <TDSBank>0.00</TDSBank>
  <TDSOther>0.00</TDSOther>
  <AdvanceTax>0.00</AdvanceTax>
  <TotalTaxPaid>15000.00</TotalTaxPaid>
</TaxPaid>
```

### **Refund/Payable**

If refund due:
```xml
<RefundAmount>2500.00</RefundAmount>
```

If tax payable:
```xml
<TaxPayable>5000.00</TaxPayable>
```

---

## 📊 ITR-2 Schema

### **Income Structure**

```xml
<IncomeDetails>
  <!-- Salary -->
  <Salary>
    <SalaryIncome>1000000.00</SalaryIncome>
    <HRAExemption>300000.00</HRAExemption>
    <StandardDeduction>50000.00</StandardDeduction>
  </Salary>
  
  <!-- House Property -->
  <HouseProperty>
    <AnnualRentalValue>0.00</AnnualRentalValue>
    <LoanInterest>0.00</LoanInterest>
    <IncomeFromHouseProperty>0.00</IncomeFromHouseProperty>
  </HouseProperty>
  
  <!-- Capital Gains -->
  <CapitalGains>
    <STCG111A>0.00</STCG111A>
    <STCGOther>0.00</STCGOther>
    <LTCG112A>0.00</LTCG112A>
    <LTCGOther>0.00</LTCGOther>
  </CapitalGains>
  
  <!-- Other Income -->
  <OtherIncome>
    <InterestIncome>0.00</InterestIncome>
    <DividendIncome>0.00</DividendIncome>
    <OtherIncome>0.00</OtherIncome>
  </OtherIncome>
  
  <GrossTotalIncome>650000.00</GrossTotalIncome>
</IncomeDetails>

<Deductions>
  <Section80C>150000.00</Section80C>
  <Section80D>0.00</Section80D>
  <Section80E>0.00</Section80E>
  <Section80G>0.00</Section80G>
  <Section80TTA>0.00</Section80TTA>
  <Section80TTB>0.00</Section80TTB>
  <TotalDeductions>150000.00</TotalDeductions>
</Deductions>
```

---

## 📊 ITR-3 Schema (Business/Profession)

```xml
<IncomeDetails>
  <BusinessIncome>500000.00</BusinessIncome>
  <ProfessionIncome>200000.00</ProfessionIncome>
  <SpeculativeIncome>0.00</SpeculativeIncome>
  <CapitalGainSTCG>0.00</CapitalGainSTCG>
  <CapitalGainLTCG>0.00</CapitalGainLTCG>
  <OtherIncome>50000.00</OtherIncome>
  <GrossTotalIncome>750000.00</GrossTotalIncome>
</IncomeDetails>

<Deductions>
  <Section80C>100000.00</Section80C>
  <Section80D>50000.00</Section80D>
  <Section80G>0.00</Section80G>
  <TotalDeductions>150000.00</TotalDeductions>
</Deductions>
```

---

## 📊 ITR-4 Schema (Presumptive - 44AD/44ADA)

```xml
<IncomeDetails>
  <Section>44AD</Section>  <!-- or 44ADA -->
  <GrossTurnover>2000000.00</GrossTurnover>
  <PresumptiveIncome>80000.00</PresumptiveIncome>  <!-- 8% of turnover -->
  <OtherIncome>20000.00</OtherIncome>
  <GrossTotalIncome>100000.00</GrossTotalIncome>
</IncomeDetails>

<Deductions>
  <Section80C>50000.00</Section80C>
  <Section80D>0.00</Section80D>
  <TotalDeductions>50000.00</TotalDeductions>
</Deductions>
```

---

## 📊 ITR-7 Schema (Trust/Section 139(4A))

```xml
<TaxableEntity>
  <PAN>AABCT1234A</PAN>
  <EntityType>trust</EntityType>  <!-- or ngo, foundation, etc -->
  <Name>ABC Educational Trust</Name>
</TaxableEntity>

<ITRForm FormName="ITR-7" AY="2023-24">
  <IncomeDetails>
    <GrossReceipts>500000.00</GrossReceipts>
    <VoluntaryContributions>200000.00</VoluntaryContributions>
    <CorpusDonations>100000.00</CorpusDonations>
    <AnonymousDonations>50000.00</AnonymousDonations>
    <BusinessIncome>100000.00</BusinessIncome>
    <InvestmentIncome>50000.00</InvestmentIncome>
    <GrossTotalIncome>500000.00</GrossTotalIncome>
  </IncomeDetails>
  
  <TaxComputation>
    <TaxableIncome>500000.00</TaxableIncome>
    <IncomeTax>25000.00</IncomeTax>
    <Surcharge>0.00</Surcharge>
    <TotalTax>25000.00</TotalTax>
  </TaxComputation>
</ITRForm>
```

---

## 🔢 Validation Rules

### **PAN Format**
- Exactly 10 characters
- Format: `AAAAA1234A`
- Example: `ABCDE1234F`
- Uppercase only

### **Assessment Year**
- Format: `YYYY-YY`
- Example: `2023-24`, `2022-23`
- Must match filing year

### **Date of Birth**
- Format: `DDMMYYYY`
- Example: `15011985`
- Must be valid date

### **Income/Deduction Values**
- All positive numbers
- Decimal format: `0.00`
- No commas or special chars
- Max 2 decimal places

### **Tax Amounts**
- Auto-calculated from income
- Must follow tax slabs
- Include surcharge & cess if applicable

---

## 💰 Tax Slab Reference

### **FY 2023-24 (AY 2024-25)**

#### **Individual - New Tax Regime (2020 onwards)**

```
≤2,50,000: Nil
2,50,001 - 5,00,000: 5%
5,00,001 - 7,50,000: 10%
7,50,001 - 10,00,000: 15%
10,00,001 - 12,50,000: 20%
12,50,001 - 15,00,000: 25%
>15,00,000: 30%
```

#### **Individual - Old Tax Regime**

```
≤1,00,000: Nil
1,00,001 - 2,50,000: 10%
2,50,001 - 5,00,000: 20%
5,00,001 - 10,00,000: 30%
>10,00,000: 30%
```

#### **Senior Citizen (60-80 years)**

```
≤3,00,000: Nil
3,00,001 - 5,00,000: 20%
>5,00,000: 30%
```

#### **Super Senior Citizen (>80 years)**

```
≤5,00,000: Nil
>5,00,000: 30%
```

### **Surcharge**

- **General**: 15% on tax if income >50L
- **Senior Citizen**: 10% if income >50L
- **Super Senior**: 5% if income >50L
- **NRI**: 20%

### **Cess**

- **New Regime**: 4% of tax (min 0%)
- **Old Regime**: 4% of tax (min 0%)

---

## 📝 Common Deduction Sections

```xml
<!-- Section 80C (LIC, PPF, ELSS, etc) - Max ₹1,50,000 -->
<Section80C>150000.00</Section80C>

<!-- Section 80D (Health Insurance) - Max ₹25,000 (₹50,000 for senior) -->
<Section80D>25000.00</Section80D>

<!-- Section 80E (Education Loan Interest) - Unlimited -->
<Section80E>100000.00</Section80E>

<!-- Section 80G (Charitable Donation) - 50% or 100% of donation -->
<Section80G>50000.00</Section80G>

<!-- Section 80TTA (Saving Account Interest) - Max ₹10,000 -->
<Section80TTA>10000.00</Section80TTA>

<!-- Section 80TTB (Interest on FD/Saving) - Max ₹50,000 -->
<Section80TTB>50000.00</Section80TTB>

<!-- Section 24B (House Property Interest) -->
<Section24B>200000.00</Section24B>
```

---

## ✅ Schema Validation Checklist

- [ ] PAN is 10 characters, uppercase
- [ ] Assessment year format: YYYY-YY
- [ ] All values are positive numbers
- [ ] Tax computed correctly per slabs
- [ ] Deductions don't exceed limits
- [ ] Gross income > deductions (if applicable)
- [ ] TDS/Advance tax entered correctly
- [ ] Refund/Payable amount is positive
- [ ] No special characters in text fields
- [ ] Date of birth is valid date

---

## 🔄 XML Generation Examples

### **Example 1: Simple ITR-1 (Salaried)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ITRDocument xmlns="http://www.incometaxindia.gov.in" DocumentType="ITR1">
  <TaxableEntity>
    <PAN>ABCDE1234F</PAN>
    <Name>Raj Kumar</Name>
    <DOB>15011985</DOB>
  </TaxableEntity>
  
  <ITRForm FormName="ITR-1" AY="2023-24">
    <IncomeDetails>
      <SalaryIncome>1000000.00</SalaryIncome>
      <HRAExemption>300000.00</HRAExemption>
      <StandardDeduction>50000.00</StandardDeduction>
      <IncomeFromHouseProperty>0.00</IncomeFromHouseProperty>
      <InterestIncome>0.00</InterestIncome>
      <OtherIncome>0.00</OtherIncome>
      <GrossTotalIncome>650000.00</GrossTotalIncome>
    </IncomeDetails>
    
    <Deductions>
      <Section80C>150000.00</Section80C>
      <Section80D>0.00</Section80D>
      <Section80E>0.00</Section80E>
      <Section80G>0.00</Section80G>
      <Section80TTA>0.00</Section80TTA>
      <TotalDeductions>150000.00</TotalDeductions>
    </Deductions>
    
    <TaxComputation>
      <TaxableIncome>500000.00</TaxableIncome>
      <IncomeTax>12500.00</IncomeTax>
      <Surcharge>0.00</Surcharge>
      <Cess>500.00</Cess>
      <TotalTax>13000.00</TotalTax>
    </TaxComputation>
    
    <TaxPaid>
      <TDSEmployer>15000.00</TDSEmployer>
      <TDSBank>0.00</TDSBank>
      <TDSOther>0.00</TDSOther>
      <AdvanceTax>0.00</AdvanceTax>
      <TotalTaxPaid>15000.00</TotalTaxPaid>
    </TaxPaid>
    
    <RefundAmount>2000.00</RefundAmount>
    
    <Verification>
      <DigitalSignature>signature_value_here</DigitalSignature>
      <SignatureDate>15/01/2024</SignatureDate>
    </Verification>
  </ITRForm>
</ITRDocument>
```

---

## 📚 References

- [Income Tax Act, 1961](https://www.incometax.gov.in/)
- [Form ITR-1](https://www.incometaxindia.gov.in/)
- [Form ITR-2](https://www.incometaxindia.gov.in/)
- [Tax Slabs FY 2023-24](https://www.incometaxindia.gov.in/)

---

**Last Updated:** January 2024  
**Version:** 1.0
