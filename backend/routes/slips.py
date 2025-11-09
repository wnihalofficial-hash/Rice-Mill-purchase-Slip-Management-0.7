from flask import Blueprint, request, jsonify, render_template
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection, get_next_bill_no
from datetime import datetime

slips_bp = Blueprint('slips', __name__)

def safe_float(value, default=0.0):
    """Safely convert value to float, handling empty strings and None"""
    try:
        if value in (None, '', ' '):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def calculate_fields(data):
    """Calculate all computed fields"""
    bags = safe_float(data.get('bags'), 0)
    avg_bag_weight = safe_float(data.get('avg_bag_weight'), 0)
    rate = safe_float(data.get('rate'), 0)
    bank_commission = safe_float(data.get('bank_commission'), 0)
    batav_percent = safe_float(data.get('batav_percent'), 1)
    shortage_percent = safe_float(data.get('shortage_percent'), 1)
    dalali_rate = safe_float(data.get('dalali_rate'), 10)
    hammali_rate = safe_float(data.get('hammali_rate'), 10)
    freight = safe_float(data.get('freight'), 0)
    rate_diff = safe_float(data.get('rate_diff'), 0)
    quality_diff = safe_float(data.get('quality_diff'), 0)
    moisture_ded = safe_float(data.get('moisture_ded'), 0)
    tds = safe_float(data.get('tds'), 0)

    net_weight = round(bags * avg_bag_weight, 2)
    amount = round(net_weight * rate, 2)
    batav = round(amount * (batav_percent / 100), 2)
    shortage = round(amount * (shortage_percent / 100), 2)
    dalali = round(net_weight * dalali_rate, 2)
    hammali = round(net_weight * hammali_rate, 2)
    total_deduction = round(bank_commission + batav + shortage + dalali + hammali + freight + rate_diff + quality_diff + moisture_ded + tds, 2)
    payable_amount = round(amount - total_deduction, 2)

    data.update({
        'net_weight': net_weight,
        'amount': amount,
        'batav': batav,
        'shortage': shortage,
        'dalali': dalali,
        'hammali': hammali,
        'freight': freight,
        'rate_diff': rate_diff,
        'quality_diff': quality_diff,
        'moisture_ded': moisture_ded,
        'tds': tds,
        'total_deduction': total_deduction,
        'payable_amount': payable_amount
    })
    return data

@slips_bp.route('/api/add-slip', methods=['POST'])
def add_slip():
    """Add a new purchase slip"""
    try:
        data = request.json
        data = calculate_fields(data)

        bill_no = get_next_bill_no()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO purchase_slips (
                company_name, company_address, document_type, vehicle_no, date,
                bill_no, party_name, material_name, ticket_no, broker,
                terms_of_delivery, sup_inv_no, gst_no, bags, avg_bag_weight,
                net_weight, rate, amount, bank_commission, batav_percent, batav,
                shortage_percent, shortage, dalali_rate, dalali, hammali_rate,
                hammali, freight, rate_diff, quality_diff, quality_diff_comment,
                moisture_ded, moisture_ded_percent, tds, total_deduction, payable_amount,
                payment_method, payment_date, payment_amount, payment_bank_account,
                payment_due_date, payment_due_comment, instalment_1, instalment_2,
                instalment_3, instalment_4, instalment_5, prepared_by, authorised_sign,
                paddy_unloading_godown
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('company_name', ''),
            data.get('company_address', ''),
            data.get('document_type', 'Purchase Slip'),
            data.get('vehicle_no', ''),
            data.get('date'),
            bill_no,
            data.get('party_name', ''),
            data.get('material_name', ''),
            data.get('ticket_no', ''),
            data.get('broker', ''),
            data.get('terms_of_delivery', ''),
            data.get('sup_inv_no', ''),
            data.get('gst_no', ''),
            data.get('bags', 0),
            data.get('avg_bag_weight', 0),
            data.get('net_weight', 0),
            data.get('rate', 0),
            data.get('amount', 0),
            data.get('bank_commission', 0),
            data.get('batav_percent', 1),
            data.get('batav', 0),
            data.get('shortage_percent', 1),
            data.get('shortage', 0),
            data.get('dalali_rate', 10),
            data.get('dalali', 0),
            data.get('hammali_rate', 10),
            data.get('hammali', 0),
            data.get('freight', 0),
            data.get('rate_diff', 0),
            data.get('quality_diff', 0),
            data.get('quality_diff_comment', ''),
            data.get('moisture_ded', 0),
            data.get('moisture_ded_percent', 0),
            data.get('tds', 0),
            data.get('total_deduction', 0),
            data.get('payable_amount', 0),
            data.get('payment_method', ''),
            data.get('payment_date', ''),
            data.get('payment_amount', 0),
            data.get('payment_bank_account', ''),
            data.get('payment_due_date', ''),
            data.get('payment_due_comment', ''),
            data.get('instalment_1', ''),
            data.get('instalment_2', ''),
            data.get('instalment_3', ''),
            data.get('instalment_4', ''),
            data.get('instalment_5', ''),
            data.get('prepared_by', ''),
            data.get('authorised_sign', ''),
            data.get('paddy_unloading_godown', '')
        ))

        slip_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Purchase slip saved successfully',
            'slip_id': slip_id,
            'bill_no': bill_no
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@slips_bp.route('/api/slips', methods=['GET'])
def get_slips():
    """Get all purchase slips"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT id, date, bill_no, party_name, material_name,
                   net_weight, payable_amount, created_at
            FROM purchase_slips
            ORDER BY id DESC
        ''')

        slips = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'slips': slips
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@slips_bp.route('/api/slip/<int:slip_id>', methods=['GET'])
def get_slip(slip_id):
    """Get a single purchase slip by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT * FROM purchase_slips WHERE id = %s', (slip_id,))
        slip = cursor.fetchone()
        cursor.close()
        conn.close()

        if slip is None:
            return jsonify({
                'success': False,
                'message': 'Slip not found'
            }), 404

        return jsonify({
            'success': True,
            'slip': slip
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@slips_bp.route('/api/slip/<int:slip_id>', methods=['PUT'])
def update_slip(slip_id):
    """Update a purchase slip"""
    try:
        data = request.json
        data = calculate_fields(data)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE purchase_slips SET
                company_name = %s, company_address = %s, document_type = %s,
                vehicle_no = %s, date = %s, payment_due_date = %s, payment_due_comment = %s,
                party_name = %s, material_name = %s, ticket_no = %s, broker = %s,
                terms_of_delivery = %s, sup_inv_no = %s, gst_no = %s, bags = %s,
                avg_bag_weight = %s, net_weight = %s, rate = %s, amount = %s,
                bank_commission = %s, batav_percent = %s, batav = %s,
                shortage_percent = %s, shortage = %s, dalali_rate = %s, dalali = %s,
                hammali_rate = %s, hammali = %s, freight = %s, rate_diff = %s,
                quality_diff = %s, quality_diff_comment = %s, moisture_ded = %s,
                moisture_ded_percent = %s, tds = %s, total_deduction = %s,
                payable_amount = %s, payment_method = %s, payment_date = %s,
                payment_amount = %s, payment_bank_account = %s,
                instalment_1 = %s, instalment_2 = %s, instalment_3 = %s,
                instalment_4 = %s, instalment_5 = %s,
                prepared_by = %s, authorised_sign = %s, paddy_unloading_godown = %s
            WHERE id = %s
        ''', (
            data.get('company_name', ''),
            data.get('company_address', ''),
            data.get('document_type', 'Purchase Slip'),
            data.get('vehicle_no', ''),
            data.get('date'),
            data.get('payment_due_date', ''),
            data.get('payment_due_comment', ''),
            data.get('party_name', ''),
            data.get('material_name', ''),
            data.get('ticket_no', ''),
            data.get('broker', ''),
            data.get('terms_of_delivery', ''),
            data.get('sup_inv_no', ''),
            data.get('gst_no', ''),
            data.get('bags', 0),
            data.get('avg_bag_weight', 0),
            data.get('net_weight', 0),
            data.get('rate', 0),
            data.get('amount', 0),
            data.get('bank_commission', 0),
            data.get('batav_percent', 1),
            data.get('batav', 0),
            data.get('shortage_percent', 1),
            data.get('shortage', 0),
            data.get('dalali_rate', 10),
            data.get('dalali', 0),
            data.get('hammali_rate', 10),
            data.get('hammali', 0),
            data.get('freight', 0),
            data.get('rate_diff', 0),
            data.get('quality_diff', 0),
            data.get('quality_diff_comment', ''),
            data.get('moisture_ded', 0),
            data.get('moisture_ded_percent', 0),
            data.get('tds', 0),
            data.get('total_deduction', 0),
            data.get('payable_amount', 0),
            data.get('payment_method', ''),
            data.get('payment_date', ''),
            data.get('payment_amount', 0),
            data.get('payment_bank_account', ''),
            data.get('instalment_1', ''),
            data.get('instalment_2', ''),
            data.get('instalment_3', ''),
            data.get('instalment_4', ''),
            data.get('instalment_5', ''),
            data.get('prepared_by', ''),
            data.get('authorised_sign', ''),
            data.get('paddy_unloading_godown', ''),
            slip_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Purchase slip updated successfully',
            'slip_id': slip_id
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@slips_bp.route('/api/slip/<int:slip_id>', methods=['DELETE'])
def delete_slip(slip_id):
    """Delete a purchase slip"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM purchase_slips WHERE id = %s', (slip_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Slip deleted successfully'
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@slips_bp.route('/print/<int:slip_id>')
def print_slip(slip_id):
    """Render print template for a slip"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT * FROM purchase_slips WHERE id = %s', (slip_id,))
        slip = cursor.fetchone()
        cursor.close()
        conn.close()

        if slip is None:
            return "Slip not found", 404

        return render_template('print_template.html', slip=slip)

    except Exception as e:
        return str(e), 400
